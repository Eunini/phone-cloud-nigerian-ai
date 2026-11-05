"""Exploratory paired maths follow-up; preserves all original benchmark files."""

import argparse
import hashlib
import json
import random
import re
import socket
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx

from bench.client import Endpoint
from bench.scoring import correct, extract, prompt

CONDITIONS = [("original", 128), ("original", 1024), ("freeform", 128), ("freeform", 1024)]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def free_prompt(item):
    return "Solve this maths problem. Explain your solution if helpful.\n\n" + item["question"]


def relaxed_number(text):
    """Last nonempty line, exactly one numeric literal; no search for the gold answer.

    This is a diagnostic, not a semantic judge. Multiple numbers/equations and
    fractions require independent review rather than guessing the intended answer.
    """
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    if not lines:
        return None
    line = lines[-1].replace("−", "-")
    if re.search(r"[=/%]", line) or re.search(r"\d\s*[-+]\s*\d", line):
        return None
    numbers = re.findall(r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", line)
    if len(numbers) != 1:
        return None
    return extract("afrimgsm", numbers[0])


def select(items):
    by_id = {}
    for item in items:
        if item["task"] == "afrimgsm":
            by_id.setdefault(item["parallel_id"], {})[item["language"]] = item
    ids = sorted(k for k, v in by_id.items() if set(v) == {"eng", "yor", "hau", "ibo"})
    random.Random(20261105).shuffle(ids)
    if len(ids) < 13:
        raise ValueError("Need parallel maths items in all four languages")
    selected = [by_id[k][language] for k in ids[:12] for language in ["eng", "yor", "hau", "ibo"]]
    selected += [by_id[ids[12]][language] for language in ["eng", "yor"]]
    return selected


def summarize(records):
    groups = []
    for style, budget in CONDITIONS:
        members = [r for r in records if r["style"] == style and r["max_tokens"] == budget]
        ok = [r for r in members if r["status"] == "ok"]
        groups.append({"style": style, "max_tokens": budget, "expected": 50,
                       "completed": len(ok), "request_errors": len(members) - len(ok),
                       "cutoffs": sum(r["finish_reason"] == "length" for r in ok),
                       "strict_correct": sum(r["strict_correct"] for r in ok),
                       "relaxed_correct": sum(r["relaxed_correct"] for r in ok),
                       "relaxed_correct_uncapped": sum(r["relaxed_correct"] and
                                                       r["finish_reason"] != "length" for r in ok),
                       "strict_unparseable": sum(r["strict_prediction"] is None for r in ok),
                       "relaxed_unparseable": sum(r["relaxed_prediction"] is None for r in ok),
                       "language_coverage": dict(Counter(r["language"] for r in ok))})
    return {"updated_at": datetime.now(timezone.utc).isoformat(), "groups": groups,
            "status": "complete" if len(records) == 200 and all(
                r["status"] == "ok" for r in records) else "partial",
            "original_scores_changed": False, "new_paid_spending_usd": 0,
            "scope": "Exploratory within-item prompt/length ablation, one CPU model; relaxed extraction is not semantic judgment or independent human review"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--server", type=Path, required=True)
    p.add_argument("--max-hours", type=float, default=2)
    p.add_argument("--prepare-only", action="store_true")
    p.add_argument("--out", type=Path, default=Path("runs/private/maths-ablation-v1"))
    a = p.parse_args()
    if not 0 < a.max_hours <= 2:
        p.error("Run is bounded to at most two hours")
    root = Path(__file__).resolve().parents[1]
    if not a.out.resolve().is_relative_to(root / "runs/private"):
        p.error("Responses must remain in runs/private")
    a.out.mkdir(parents=True, exist_ok=True, mode=0o700)
    report = root / "report/maths-ablation"
    report.mkdir(parents=True, exist_ok=True)
    weights = root / "models/qwen2.5-1.5b-instruct-q4_k_m.gguf"
    metadata = json.loads(weights.with_suffix(".provenance.json").read_text())
    if sha(weights) != metadata["sha256"]:
        raise ValueError("Weights differ from recorded research model")
    source = root / "data/prepared/items.jsonl"
    selected = select([json.loads(x) for x in source.read_text().splitlines()])
    plan = {"created_at": datetime.now(timezone.utc).isoformat(),
            "scope": "Exploratory follow-up on previously evaluated items; not independent confirmation",
            "model": metadata, "binary_sha256": sha(a.server), "source_sha256": sha(source),
            "selected_ids": [x["id"] for x in selected], "seed": 20261105,
            "conditions": [list(c) for c in CONDITIONS], "context_tokens_all_conditions": 4096,
            "threads": 2, "gpu_layers": 0, "temperature": 0,
            "original_prompt_version": "fixed-en-instructions-v1",
            "free_prompt_prefix": free_prompt({"question": ""}),
            "scoring_policy": relaxed_number.__doc__,
            "module_sha256": sha(__file__), "primary_original_results_unchanged": True}
    plan_path = report / "plan.json"
    if plan_path.exists():
        old = json.loads(plan_path.read_text())
        if {k: v for k, v in old.items() if k != "created_at"} != {
            k: v for k, v in plan.items() if k != "created_at"
        }:
            raise ValueError("Plan changed: preserve this experiment and use a new version")
    else:
        plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    if a.prepare_only:
        print(json.dumps({"planned_cases": 50, "conditions": 4, "inference_requests": 0}))
        return
    with socket.socket() as check:
        check.bind(("127.0.0.1", 18763))
    command = [str(a.server.resolve()), "-m", str(weights), "--alias", "maths-pilot",
               "--host", "127.0.0.1", "--port", "18763", "--ctx-size", "4096",
               "--threads", "2", "--threads-batch", "2", "--parallel", "1",
               "--n-gpu-layers", "0", "--seed", "2026", "--cache-ram", "0"]
    journal = a.out / "responses.jsonl"
    records = [json.loads(x) for x in journal.read_text().splitlines()] if journal.exists() else []
    seen = {(r["id"], r["style"], r["max_tokens"]) for r in records}
    jobs = [(item, style, limit) for item in selected for style, limit in CONDITIONS]
    random.Random(20261105).shuffle(jobs)
    start = time.monotonic()
    endpoint = Endpoint("http://127.0.0.1:18763/v1", "maths-pilot", timeout=180)
    with (a.out / "server.log").open("w") as log:
        server = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(120):
                if server.poll() is not None:
                    raise RuntimeError("Model server exited; inspect private server log")
                try:
                    if httpx.get("http://127.0.0.1:18763/health", timeout=3).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(1)
            else:
                raise RuntimeError("Server readiness timeout")
            with journal.open("a") as stream:
                journal.chmod(0o600)
                for item, style, budget in jobs:
                    if (item["id"], style, budget) in seen:
                        continue
                    if time.monotonic() - start >= a.max_hours * 3600:
                        break
                    record = {"id": item["id"], "language": item["language"],
                              "style": style, "max_tokens": budget}
                    try:
                        result = endpoint.complete([{"role": "user", "content":
                                                     prompt(item) if style == "original" else free_prompt(item)}], budget)
                        prediction = relaxed_number(result["text"])
                        record.update(result, status="ok", strict_correct=correct(item, result["text"]),
                                      strict_prediction=extract("afrimgsm", result["text"]),
                                      relaxed_prediction=prediction,
                                      relaxed_correct=prediction is not None and prediction == extract("afrimgsm", item["answer"]))
                    except Exception as error:
                        record.update(status="error", error_type=type(error).__name__)
                    stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                    stream.flush()
                    records.append(record)
                    (report / "results.json").write_text(json.dumps(summarize(records), indent=2) + "\n")
                    if len(records) % 10 == 0:
                        print(json.dumps({"completed_attempts": len(records), "total": 200}), flush=True)
        finally:
            endpoint.close()
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            (report / "shutdown.json").write_text(json.dumps({"server_stopped": True,
                                                            "recorded_attempts": len(records)}) + "\n")


if __name__ == "__main__":
    main()
