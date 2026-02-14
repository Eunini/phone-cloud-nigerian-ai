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
        try:
            self.process = psutil.Process(pid) if pid else None
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            self.process = None
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


def measure_question(endpoint, item, *, translator=None, max_tokens=128, server_pid=None):
    """Keep target-API accounting when a separate translation stage fails."""
    start = time.perf_counter()
    record = {"target_request_attempted": False}
    stage = "translation"
    with MemorySampler(server_pid) as memory, MemorySampler(os.getpid()) as client_memory:
        try:
            translation_start = time.perf_counter()
            translated = translator.item_to_english(item) if translator else item
            record["translation_seconds"] = (
                time.perf_counter() - translation_start if translator else 0
            )
            stage = "inference"
            record["target_request_attempted"] = True
            result = endpoint.complete([{"role": "user", "content": prompt(translated)}], max_tokens)
            output = result["text"]
            record.update(
                result,
                answer_correct=correct(item, output),
                prediction=extract(item["task"], output),
            )
            stage = "back_translation"
            back_start = time.perf_counter()
            displayed = (
                translator.text(output, "eng", item["language"])
                if translator and item["language"] != "eng"
                else output
            )
            record.update(
                status="ok",
                correct=record["answer_correct"],
                translated_back=displayed if translator else None,
                back_translation_seconds=time.perf_counter() - back_start if translator else 0,
            )
        except Exception as error:
            # Never replace target-API bytes with a local translator's HTTP bytes.
            record.update(
                status="error", error_type=type(error).__name__, error_stage=stage, correct=False
            )
            if not record["target_request_attempted"]:
                record.update(request_body_bytes=0, response_body_bytes=0, mb_per_question=0.0)
            if isinstance(error, CompletionFailure):
                if stage == "inference":
                    record.update(error.telemetry, error_type=error.error_type)
                else:
                    record.update(
                        translation_error_type=error.error_type,
                        translation_http_status=error.telemetry.get("http_status"),
                    )
    record.update(
        peak_server_rss_bytes_sampled=memory.peak,
        peak_client_rss_bytes_sampled=client_memory.peak,
        memory_sampling_interval_seconds=0.05,
        memory_scope="separate server-PID and client-PID RSS peaks across translation, answer and presentation; excludes external process trees and GPU allocations",
        end_to_end_seconds=time.perf_counter() - start,
    )
    return record


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
    p.add_argument("--replicate", type=int, help="Independent timing repetition identifier")
    p.add_argument(
        "--max-attempts-per-item",
        type=int,
        default=3,
        help="Retry only request failures, never an incorrect completed answer",
    )
    p.add_argument("--translate", action="store_true")
    p.add_argument(
        "--translation-endpoint",
        help="Loopback translator for phone GGUF inference; requires --translate",
    )
    p.add_argument("--translation-model")
    p.add_argument("--translation-revision")
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
    if (
        a.min_interval < 0
        or (a.max_new_requests is not None and a.max_new_requests < 1)
        or a.max_attempts_per_item < 1
    ):
        p.error("Use a nonnegative interval and positive new-request budget")
    endpoint = Endpoint(a.endpoint, a.model, os.environ.get(a.key_env))
    items = [json.loads(x) for x in a.items.read_text().splitlines() if x.strip()]
    expected_groups = Counter((r["language"], r["task"]) for r in items)
    random.Random(2026).shuffle(items)
    if a.limit:
        items = items[: a.limit]
    translator = None
    if a.translate:
        from bench.translate import EndpointTranslator, Translator

        if a.translation_endpoint:
            if not a.translation_model or not a.translation_revision:
                p.error("Record both the local translator model and weights revision")
            translator = EndpointTranslator(
                a.translation_endpoint, a.translation_model, a.translation_revision
            )
        else:
            translator = Translator()
    elif a.translation_endpoint:
        p.error("--translation-endpoint requires --translate")
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
    if translator:
        identity["translator"] = translator.identity
    if a.replicate is not None:
        identity["replicate"] = a.replicate
    run_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    existing = [json.loads(x) for x in a.out.read_text().splitlines()] if a.out.exists() else []
    if any(row["run_id"] != run_id for row in existing):
        raise ValueError("Refusing to mix incompatible runs in one result file")
    attempts = Counter(row["id"] for row in existing)
    completed = {row["id"] for row in existing if row["status"] == "ok"} | {
        item for item, count in attempts.items() if count >= a.max_attempts_per_item
    }
    # Warmup is separate from scored requests and has its own body/usage accounting.
    try:
        warmup = {
            **endpoint.complete([{"role": "user", "content": "Return the word ready."}], 8),
            "status": "ok",
        }
    except CompletionFailure as error:
        warmup = {**error.telemetry, "status": "error", "error_type": error.error_type}
    with a.out.with_suffix(".warmup.jsonl").open("a") as warmup_stream:
        warmup_stream.write(
            json.dumps(
                {**warmup, "run_id": run_id, "timestamp": datetime.now(timezone.utc).isoformat()}
            )
            + "\n"
        )
    if warmup["status"] != "ok":
        endpoint.close()
        if translator and hasattr(translator, "close"):
            translator.close()
        raise SystemExit(
            "Warmup failed; sanitized telemetry saved. Resolve provider access/quota before resuming."
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
                record.update(
                    measure_question(
                        endpoint,
                        item,
                        translator=translator,
                        max_tokens=a.max_tokens,
                        server_pid=a.server_pid,
                    )
                )
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                stream.flush()
                attempted += 1
                if attempted % 100 == 0:
                    print(f"Saved {attempted} new question attempts in this batch.", flush=True)
                if record.get("http_status") in {401, 403, 429}:
                    print(
                        "Stopped after authentication/quota response; saved progress. Resume after resolving provider access/quota."
                    )
                    break
                if a.server_pid and not psutil.pid_exists(a.server_pid):
                    print(
                        "Local model process exited; saved partial results. Check memory and the server log before resuming."
                    )
                    break
                if a.max_new_requests and attempted >= a.max_new_requests:
                    print("Request budget reached; saved progress for a later resume.")
                    break
                time.sleep(max(0, a.min_interval - (time.perf_counter() - start)))
    finally:
        endpoint.close()
        if translator and hasattr(translator, "close"):
            translator.close()


if __name__ == "__main__":
    main()
