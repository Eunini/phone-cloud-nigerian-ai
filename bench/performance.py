"""Summarize completed fixed-sample repeats separately from full-set accuracy."""

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


def percentile(values, fraction):
    """Linear interpolation between sorted observations, including both endpoints."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize(paths, items):
    expected = {r["id"]: (r["language"], r["task"]) for r in items}
    groups = defaultdict(list)
    for identity, group in expected.items():
        groups[group].append(identity)
    if (
        len(items) != 120
        or len(expected) != 120
        or len(groups) != 12
        or any(len(ids) != 10 for ids in groups.values())
    ):
        raise ValueError("Use the predeclared 120 distinct items, ten per language/task")
    if len(paths) != 3:
        raise ValueError("Require all three repetitions")
    rows, inputs, run_ids, signatures = [], [], set(), set()
    for repetition, path in enumerate(paths, 1):
        raw = Path(path).read_bytes()
        if not raw.endswith(b"\n"):
            raise ValueError("Timing inputs must have complete lines")
        records = [json.loads(line) for line in raw.splitlines()]
        if len(records) != 120 or {r["id"] for r in records} != set(expected):
            raise ValueError("Each repetition must contain the same 120 items exactly once")
        ids = {r["run_id"] for r in records}
        if len(ids) != 1 or ids & run_ids:
            raise ValueError("Repetitions need distinct, unmixed run identities")
        run_ids.update(ids)
        for row in records:
            if (row["language"], row["task"]) != expected[row["id"]]:
                raise ValueError("Timing language/task disagrees with the selected item")
            if row["replicate"] != repetition or row["status"] != "ok" or row["translate"]:
                raise ValueError("Require successful, untranslated repetitions in order")
            signatures.add(
                tuple(
                    row[key]
                    for key in (
                        "model",
                        "model_revision",
                        "items_sha256",
                        "prompt_version",
                        "max_tokens",
                    )
                )
            )
            for key in (
                "end_to_end_seconds",
                "latency_seconds",
                "time_to_first_word_seconds",
                "peak_server_rss_bytes_sampled",
                "peak_client_rss_bytes_sampled",
            ):
                if (
                    not isinstance(row.get(key), (float, int))
                    or not math.isfinite(row[key])
                    or row[key] <= 0
                ):
                    raise ValueError("Missing or invalid timing/memory observation: " + key)
            rate = row.get("decode_words_per_second")
            if rate is not None and (not math.isfinite(rate) or rate <= 0):
                raise ValueError("Invalid decode rate")
        rows.extend(records)
        inputs.append(
            {
                "path": str(path),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "records": len(records),
                "run_id": next(iter(ids)),
            }
        )
    if len(signatures) != 1:
        raise ValueError("Model, prompt, budget or sample changed between repetitions")
    model, weights, sample, prompt, budget = next(iter(signatures))
    grouped = defaultdict(list)
    grouped[("all", "all")] = rows
    for row in rows:
        grouped[(row["language"], row["task"])].append(row)
    result = []
    for (language, task), records in sorted(
        grouped.items(), key=lambda entry: (entry[0] != ("all", "all"), entry[0])
    ):
        texts = defaultdict(set)
        for row in records:
            texts[row["id"]].add(row["text"])
        latencies = [r["end_to_end_seconds"] for r in records]
        first_words = [r["time_to_first_word_seconds"] for r in records]
        rates = [
            r["decode_words_per_second"]
            for r in records
            if r.get("decode_words_per_second") is not None
        ]
        result.append(
            {
                "language": language,
                "task": task,
                "requests": len(records),
                "distinct_items": len(texts),
                "repetitions": 3,
                "median_end_to_end_seconds": statistics.median(latencies),
                "p95_end_to_end_seconds": percentile(latencies, 0.95),
                "median_first_word_seconds": statistics.median(first_words),
                "p95_first_word_seconds": percentile(first_words, 0.95),
                "median_decode_words_per_second": statistics.median(rates) if rates else None,
                "decode_rate_observations": len(rates),
                "max_sampled_server_rss_bytes": max(
                    r["peak_server_rss_bytes_sampled"] for r in records
                ),
                "max_sampled_client_rss_bytes": max(
                    r["peak_client_rss_bytes_sampled"] for r in records
                ),
                "items_with_different_text_across_repeats": sum(len(v) > 1 for v in texts.values()),
            }
        )
    return {
        "model": model,
        "model_revision": weights,
        "items_sha256": sample,
        "prompt_version": prompt,
        "max_tokens": budget,
        "inputs": inputs,
        "scope": "Shared Linux CPU host, two-thread model server, sequential loopback requests; unknown hosting price",
        "caveats": [
            "360 observations repeat 120 items; these are not 360 independent questions",
            "Persistent model server and prompt cache; repeated sample order can benefit from caching",
            "Shared host load is uncontrolled; observations are not a phone, WAN, reserved-core or production SLA measurement",
            "End-to-end time excludes model loading, warmup, inter-request pauses and controller downtime",
            "RSS peaks are sampled every 50 ms, not total host memory; decode rate is undefined for some one-chunk responses",
            "p95 uses linear interpolation over the observed sample; no population confidence bound is claimed",
            "Timing rows never enter the full-set accuracy denominator",
        ],
        "groups": result,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", type=Path, nargs=3)
    parser.add_argument("--items", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.runs, [json.loads(x) for x in args.items.read_text().splitlines()])
    if result["items_sha256"] != hashlib.sha256(args.items.read_bytes()).hexdigest():
        raise ValueError("Timing selection hash does not match the recorded sample")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n")
    with args.out.with_suffix(".csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(result["groups"][0]))
        writer.writeheader()
        writer.writerows(result["groups"])
    print(json.dumps(result["groups"][0], indent=2))


if __name__ == "__main__":
    main()
