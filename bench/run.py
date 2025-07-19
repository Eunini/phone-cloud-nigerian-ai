import argparse
import hashlib
import json
import os
import platform
import random
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import psutil

from bench.client import CompletionFailure, Endpoint
from bench.scoring import PROMPT_VERSION, correct, extract, prompt


class MemorySampler:
    def __init__(self, pid):
        self.process = psutil.Process(pid) if pid else None
        self.stop = threading.Event()
        self.peak = None
        self.thread = None

    def __enter__(self):
        if self.process:

            def sample():
                while not self.stop.is_set():
                    try:
                        rss = self.process.memory_info().rss
                        self.peak = max(self.peak or 0, rss)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        return
                    self.stop.wait(0.05)

            self.thread = threading.Thread(target=sample, daemon=True)
            self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set()
        if self.thread:
            self.thread.join()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--items", type=Path, default=Path("data/prepared/items.jsonl"))
    p.add_argument("--endpoint", required=True, help="API root ending in /v1")
    p.add_argument("--model", required=True)
    p.add_argument("--label", help="Human-readable run/model label if the server uses an alias")
    p.add_argument("--model-revision", required=True, help="Weights hash or provider version")
    p.add_argument("--placement", choices=["local", "cloud"], required=True)
    p.add_argument("--key-env", default="BENCH_API_KEY")
    p.add_argument("--device", required=True, help="Actual device/server description")
    p.add_argument("--server-pid", type=int)
    p.add_argument("--translate", action="store_true")
    p.add_argument("--limit", type=int)
    p.add_argument(
        "--max-new-requests",
        type=int,
        help="Stop and save after this many new questions; resume the same full run later",
    )
    p.add_argument("--max-tokens", type=int, default=128)
    p.add_argument(
        "--min-interval",
        type=float,
        default=0,
        help="Minimum seconds between request starts; respect provider quotas",
    )
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.min_interval < 0 or (a.max_new_requests is not None and a.max_new_requests < 1):
        p.error("Use a nonnegative interval and positive new-request budget")
    endpoint = Endpoint(a.endpoint, a.model, os.environ.get(a.key_env))
    items = [json.loads(x) for x in a.items.read_text().splitlines() if x.strip()]
    expected_groups = Counter((r["language"], r["task"]) for r in items)
    random.Random(2026).shuffle(items)
    if a.limit:
        items = items[: a.limit]
    translator = None
    if a.translate:
        from bench.translate import Translator

        translator = Translator()
    identity = {
        "model": a.label or a.model,
        "endpoint_model": a.model,
        "model_revision": a.model_revision,
        "endpoint": endpoint.url,
        "placement": a.placement,
        "device": a.device,
        "platform": platform.platform(),
        "prompt_version": PROMPT_VERSION,
        "translate": a.translate,
        "max_tokens": a.max_tokens,
        "min_interval_seconds": a.min_interval,
        "items_sha256": hashlib.sha256(a.items.read_bytes()).hexdigest(),
        "partial": a.limit is not None,
    }
    run_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    existing = [json.loads(x) for x in a.out.read_text().splitlines()] if a.out.exists() else []
    if any(row["run_id"] != run_id for row in existing):
        raise ValueError("Refusing to mix incompatible runs in one result file")
    completed = {row["id"] for row in existing if row["status"] == "ok"}
    # Warmup is separate from scored requests and has its own body/usage accounting.
    warmup = endpoint.complete([{"role": "user", "content": "Return the word ready."}], 8)
    with a.out.with_suffix(".warmup.jsonl").open("a") as warmup_stream:
        warmup_stream.write(
            json.dumps(
                {**warmup, "run_id": run_id, "timestamp": datetime.now(timezone.utc).isoformat()}
            )
            + "\n"
        )
    try:
        attempted = 0
        with a.out.open("a") as stream:
            for item in items:
                if item["id"] in completed:
                    continue
                start = time.perf_counter()
                record = {
                    **identity,
                    "run_id": run_id,
                    "id": item["id"],
                    "language": item["language"],
                    "task": item["task"],
                    "expected_group_items": expected_groups[(item["language"], item["task"])],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                try:
                    translation_start = time.perf_counter()
                    translated = translator.item_to_english(item) if translator else item
                    translation_seconds = (
                        time.perf_counter() - translation_start if translator else 0
                    )
                    with MemorySampler(a.server_pid) as memory:
                        result = endpoint.complete(
                            [{"role": "user", "content": prompt(translated)}], a.max_tokens
                        )
                    output = result["text"]
                    # Scores are canonical letters/labels/numbers; translate presentation separately.
                    back_start = time.perf_counter()
                    displayed = (
                        translator.text(output, "eng", item["language"])
                        if translator and item["language"] != "eng"
                        else output
                    )
                    record.update(
                        result,
                        status="ok",
                        correct=correct(item, output),
                        prediction=extract(item["task"], output),
                        translated_back=displayed if translator else None,
                        translation_seconds=translation_seconds,
                        back_translation_seconds=time.perf_counter() - back_start
                        if translator
                        else 0,
                        peak_server_rss_bytes_sampled=memory.peak,
                        memory_sampling_interval_seconds=0.05,
                    )
                except Exception as error:
                    # Do not dump provider errors, authorization headers, or arbitrary response bodies.
                    record.update(status="error", error_type=type(error).__name__, correct=False)
                    if isinstance(error, CompletionFailure):
                        record.update(error.telemetry, error_type=error.error_type)
                record["end_to_end_seconds"] = time.perf_counter() - start
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                stream.flush()
                attempted += 1
                if record.get("http_status") in {401, 403, 429}:
                    print(
                        "Stopped after authentication/quota response; saved progress. Resume after resolving provider access/quota."
                    )
                    break
                if a.max_new_requests and attempted >= a.max_new_requests:
                    print("Request budget reached; saved progress for a later resume.")
                    break
                time.sleep(max(0, a.min_interval - (time.perf_counter() - start)))
    finally:
        endpoint.close()


if __name__ == "__main__":
    main()
