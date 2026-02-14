"""Finite free-tier benchmark continuation, respecting Pacific daily quota resets.

This starts no cloud resources, changes no billing settings, and sends no messages.
Only the fixed public IrokoBench questions are sent to the verified Gemini model.
"""

import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")


def day(timestamp):
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(PACIFIC).date()


def read_rows(path):
    return (
        [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if path.exists()
        else []
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--items", type=Path, default=Path("data/prepared/items.jsonl"))
    p.add_argument("--out", type=Path, default=Path("report/runs/gemini-flash-lite-full.jsonl"))
    p.add_argument("--max-quota-days", type=int, default=30)
    a = p.parse_args()
    state = Path.home() / ".local/state/afri-research"
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = (state / "gemini-benchmark.lock").open("w")
    os.chmod(lock.name, 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    lock.write(str(os.getpid()))
    lock.flush()
    items = {r["id"] for r in read_rows(a.items)}
    if len(items) != 3400:
        raise ValueError("Expected the full audited IrokoBench selection")
    starting_day = datetime.now(PACIFIC).date()
    keydir = Path.home() / ".config/afri-research"
    while (datetime.now(PACIFIC).date() - starting_day).days < a.max_quota_days:
        records = read_rows(a.out)
        counts = Counter(r["id"] for r in records)
        completed = {r["id"] for r in records if r["status"] == "ok"} | {
            key for key, n in counts.items() if n >= 3
        }
        today = datetime.now(PACIFIC).date()
        calls_today = sum(day(r["timestamp"]) == today for r in records)
        warmups = read_rows(a.out.with_suffix(".warmup.jsonl"))
        quota_seen = any(
            r.get("http_status") == 429 and day(r["timestamp"]) == today for r in records + warmups
        )
        progress = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_items": len(items),
            "completed_or_three_failed_attempts": len(items & completed),
            "attempts_today": calls_today,
            "quota_day_timezone": "America/Los_Angeles",
            "all_items_attempted": items <= set(counts),
            "finished": items <= completed,
            "api_billing": "owner-confirmed free tier, billing unlinked",
        }
        a.out.with_suffix(".progress.json").write_text(json.dumps(progress, indent=2) + "\n")
        if items <= completed:
            print(
                "Finite commercial benchmark finished; terminal request failures remain explicitly recorded.",
                flush=True,
            )
            return
        if calls_today >= 450 or quota_seen:
            next_day = datetime.combine(
                today + timedelta(days=1), datetime.min.time(), PACIFIC
            ) + timedelta(minutes=5)
            while datetime.now(PACIFIC) < next_day:
                time.sleep(min(30, max(1, (next_day - datetime.now(PACIFIC)).total_seconds())))
            continue
        profile = json.loads((keydir / "gemini_profile.json").read_text())
        if profile.get("free_tier") is not True or profile.get("billing_linked") is not False:
            raise ValueError("Verified free-tier/no-billing profile is required")
        env = os.environ.copy()
        env["BENCH_API_KEY"] = (keydir / "gemini_api_key").read_text().strip()
        command = [
            sys.executable,
            "-m",
            "bench.run",
            "--items",
            str(a.items),
            "--endpoint",
            "https://generativelanguage.googleapis.com/v1beta/openai",
            "--model",
            "gemini-3.1-flash-lite-preview",
            "--label",
            "gemini-3.1-flash-lite-preview-free",
            "--model-revision",
            "3.1-flash-lite-preview-03-2026",
            "--placement",
            "cloud",
            "--device",
            "Google Gemini Developer API; provider hardware undisclosed",
            "--min-interval",
            "5",
            "--max-new-requests",
            str(450 - calls_today),
            "--out",
            str(a.out),
        ]
        result = subprocess.run(command, env=env)
        del env["BENCH_API_KEY"]
        if result.returncode:
            last = read_rows(a.out.with_suffix(".warmup.jsonl"))[-1:]
            if not last or last[0].get("http_status") != 429:
                raise SystemExit(
                    "Benchmark continuation stopped; progress retained and no paid fallback used"
                )
    raise SystemExit("Finite quota-day limit reached; partial progress retained")


if __name__ == "__main__":
    main()
