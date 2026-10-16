"""Finite, resumable CPU-server study; never presents workspace results as a phone."""

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx
from huggingface_hub import get_hf_file_metadata, hf_hub_download, hf_hub_url

from bench.device import metadata

LLAMA_REVISION = "6050b467c07a95c7b87debd4ddac2f8ba8d9b807"
DATA_SHA256 = "c9bdac81650e6c4b9c3c6aaf36730df05fe975628149643248c4da946dc3f07f"
TIMING_SHA256 = "d6c750ecd650a86e27959097465506dcf216d389f18985c7eab5ef5c0d0dc0bf"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def audit_run(path, expected_ids):
    """Completed answers stay fixed; failed requests need three recorded attempts."""
    rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    counts = Counter(row["id"] for row in rows)
    if set(counts) - expected_ids:
        raise ValueError("Unexpected question IDs in workspace run")
    if len({row["run_id"] for row in rows}) > 1:
        raise ValueError("Mixed run identities in workspace run")
    successful = {row["id"] for row in rows if row["status"] == "ok"}
    terminal = successful | {item for item, count in counts.items() if count >= 3}
    return {
        "complete": terminal == expected_ids,
        "unique_items": len(counts),
        "successful_items": len(successful),
        "attempts": len(rows),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--server", type=Path, required=True)
    p.add_argument("--scratch", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("report/runs/workspace-cpu"))
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--max-hours", type=float, default=24)
    p.add_argument("--port", type=int, default=18991)
    a = p.parse_args()
    if a.threads < 1 or not 0 < a.max_hours <= 48:
        p.error("Use positive threads and a runtime limit of at most 48 hours")
    a.server = a.server.absolute()
    a.scratch = a.scratch.absolute()
    if a.scratch.is_relative_to(Path.cwd()):
        p.error("Model scratch must be outside the repository")
    a.scratch.mkdir(parents=True, exist_ok=True)
    a.out.mkdir(parents=True, exist_ok=True)
    lock = (a.scratch / "workspace.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    deadline = time.monotonic() + a.max_hours * 3600

    def terminate(*_):
        raise SystemExit("Workspace study interrupted; flushed records retained")

    signal.signal(signal.SIGTERM, terminate)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    checkout = a.server.parents[2]
    revision = subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != LLAMA_REVISION:
        raise ValueError("Build the pinned llama.cpp revision before running")
    if subprocess.check_output(["git", "-C", str(checkout), "status", "--porcelain"], text=True):
        raise ValueError("llama.cpp checkout contains unrecorded changes")
    items = Path("data/prepared/items.jsonl")
    if digest(items) != DATA_SHA256:
        raise ValueError("Evaluation data differs from the audited selection")
    subprocess.run([sys.executable, "-m", "bench.timing"], check=True, timeout=60)
    timing = Path("data/prepared/timing120.jsonl")
    if digest(timing) != TIMING_SHA256:
        raise ValueError("Timing sample differs from the predeclared selection")
    expected = {
        items: {json.loads(line)["id"] for line in items.read_text().splitlines()},
        timing: {json.loads(line)["id"] for line in timing.read_text().splitlines()},
    }
    provenance_path = a.out / "provenance.json"
    identity = {
        "evaluation_source_commit": source,
        "llama_cpp_revision": revision,
        "server_binary_sha256": digest(a.server),
        "items_sha256": DATA_SHA256,
        "timing_sha256": TIMING_SHA256,
        "threads": a.threads,
        "port": a.port,
        "models": ["qwen", "smollm"],
        "quantizations": ["Q4_K_M", "Q8_0"],
        "placement": "cloud",
        "hardware_scope": "shared Linux CPU server; GPU layers zero; no phone/laptop evidence",
        "billing": "workspace hosting price unknown; full hosting cost must remain unknown",
        "protocol": "Full 3400-item accuracy, three 120-item timing repeats; Qwen Q4 self-translation condition selected before CPU results",
    }
    if provenance_path.exists():
        provenance = json.loads(provenance_path.read_text())
        if any(provenance[key] != value for key, value in identity.items()):
            raise ValueError("Existing workspace provenance differs; use a new output directory")
    else:
        provenance = {**identity, "device": metadata(), "started_at": datetime.now(timezone.utc).isoformat()}
        write_json(provenance_path, provenance)
    device = json.dumps(provenance["device"], sort_keys=True)
    models = json.loads(Path("configs/models.json").read_text())["models"]
    progress = {"status": "running", "conditions": [], "deadline_hours": a.max_hours}
    write_json(a.out / "progress.json", progress)

    def run(command):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Finite workspace runtime budget reached")
        subprocess.run(command, check=True, timeout=min(21600, remaining))

    try:
        for model_key in identity["models"]:
            model = models[model_key]
            for quant in identity["quantizations"]:
                label = f"cpu-server-{model_key}-{quant}"
                file_name = model["files"][quant]
                info = get_hf_file_metadata(
                    hf_hub_url(model["repo"], file_name, revision=model["revision"]), token=False
                )
                if info.size is None or len(info.etag or "") != 64:
                    raise ValueError("Expected published GGUF size and SHA256")
                # Reuse this study's previously verified Qwen Q4 rather than duplicate it.
                cached = Path("models") / file_name
                if cached.is_file() and digest(cached) == info.etag:
                    weights, owned = cached.absolute(), False
                else:
                    cached = a.scratch / file_name
                    if not cached.exists() and shutil.disk_usage(a.scratch).free < info.size + 268435456:
                        raise OSError("Insufficient scratch space for the next model")
                    weights = Path(hf_hub_download(
                        model["repo"], file_name, revision=model["revision"],
                        local_dir=a.scratch, token=False,
                    ))
                    owned = True
                if digest(weights) != info.etag or weights.stat().st_size != info.size:
                    raise ValueError("Downloaded GGUF does not match published SHA256/size")
                # Never displace another service on the fixed, resumable loopback endpoint.
                with socket.socket() as port_check:
                    port_check.bind(("127.0.0.1", a.port))
                command = [
                    str(a.server), "-m", str(weights), "--alias", "local",
                    "--host", "127.0.0.1", "--port", str(a.port),
                    "--ctx-size", "2048", "--threads", str(a.threads),
                    "--threads-batch", str(a.threads), "--parallel", "1",
                    "--n-gpu-layers", "0", "--seed", "2026",
                ]
                condition = {
                    "model": label, "repo": model["repo"], "revision": model["revision"],
                    "license": model["license"], "sha256": info.etag, "bytes": info.size,
                    "server_command": command, "load_before": os.getloadavg(), "runs": [],
                }
                write_json(a.out / (label + ".provenance.json"), condition)
                with (a.out / (label + ".server.log")).open("a") as log:
                    server = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                    try:
                        endpoint = f"http://127.0.0.1:{a.port}"
                        with httpx.Client(timeout=3) as client:
                            for _ in range(180):
                                if server.poll() is not None:
                                    raise RuntimeError("CPU server exited; inspect retained server log")
                                try:
                                    if client.get(endpoint + "/health").status_code == 200:
                                        break
                                except httpx.HTTPError:
                                    pass
                                time.sleep(1)
                            else:
                                raise TimeoutError("CPU model failed to become ready")
                        runs = [(items, "full", None, False)] + [
                            (timing, f"timing-{n}", n, False) for n in range(1, 4)
                        ]
                        if model_key == "qwen" and quant == "Q4_K_M":
                            runs += [(items, "translated-full", None, True)]
                            runs += [(timing, f"translated-timing-{n}", n, True) for n in range(1, 4)]
                        for data, suffix, repeat, translate in runs:
                            out = a.out / (label + "-" + suffix + ".jsonl")
                            args = [
                                sys.executable, "-m", "bench.run", "--items", str(data),
                                "--endpoint", endpoint + "/v1", "--model", "local",
                                "--label", label + ("-translated" if translate else ""),
                                "--model-revision", info.etag, "--placement", "cloud",
                                "--device", device, "--server-pid", str(server.pid), "--out", str(out),
                            ]
                            if repeat is not None:
                                args += ["--limit", "120", "--replicate", str(repeat)]
                            if translate:
                                args += [
                                    "--translate", "--translation-endpoint", endpoint + "/v1",
                                    "--translation-model", "local", "--translation-revision", info.etag,
                                ]
                            for _ in range(3):
                                if audit_run(out, expected[data])["complete"]:
                                    break
                                if server.poll() is not None:
                                    raise RuntimeError("CPU model process stopped during evaluation")
                                run(args)
                            audit = audit_run(out, expected[data])
                            condition["runs"].append({"file": out.name, **audit})
                            write_json(a.out / (label + ".provenance.json"), condition)
                            if not audit["complete"]:
                                raise RuntimeError("Incomplete CPU evaluation; retained partial evidence")
                    finally:
                        server.terminate()
                        try:
                            server.wait(timeout=15)
                        except subprocess.TimeoutExpired:
                            server.kill()
                            server.wait()
                condition["load_after"] = os.getloadavg()
                write_json(a.out / (label + ".provenance.json"), condition)
                progress["conditions"].append(condition)
                write_json(a.out / "progress.json", progress)
                if owned:
                    weights.unlink()  # Only this runner's scratch download, after all recorded runs.
        progress["status"] = "complete"
    except BaseException as error:
        progress.update(status="stopped", error_type=type(error).__name__)
        raise
    finally:
        progress["updated_at"] = datetime.now(timezone.utc).isoformat()
        write_json(a.out / "progress.json", progress)


if __name__ == "__main__":
    main()
