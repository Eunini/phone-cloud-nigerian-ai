"""Start the copied GGUF on the actual device, score 12 items and stop its server."""

import argparse
import hashlib
import json
import subprocess
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from bench.device import metadata


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model-file", type=Path, default=Path("models/model.gguf"))
    p.add_argument("--server", type=Path, default=Path(".llama-cpp/build/bin/llama-server"))
    p.add_argument("--label", default="qwen-1.5b-Q4_K_M-phone-smoke")
    a = p.parse_args()
    with a.model_file.open("rb") as source:
        if source.read(4) != b"GGUF":
            raise ValueError("Copy the real GGUF before running the smoke check")
    with a.model_file.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    endpoint = f"http://127.0.0.1:{port}"
    device = metadata()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path("report/runs") / ("phone-smoke-" + stamp)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".device.json").write_text(json.dumps(device, indent=2) + "\n")
    with out.with_suffix(".server.log").open("w") as log:
        server = subprocess.Popen(
            [
                str(a.server),
                "-m",
                str(a.model_file),
                "--alias",
                "local",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--ctx-size",
                "2048",
                "--threads",
                "4",
                "--parallel",
                "1",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            with httpx.Client(timeout=3) as client:
                for _ in range(180):
                    if server.poll() is not None:
                        raise RuntimeError("Phone model server stopped; preserve the server log")
                    try:
                        if client.get(endpoint + "/health").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(1)
                else:
                    raise RuntimeError("Phone model did not become ready")
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "bench.run",
                    "--endpoint",
                    endpoint + "/v1",
                    "--model",
                    "local",
                    "--label",
                    a.label,
                    "--model-revision",
                    digest,
                    "--placement",
                    "local",
                    "--device",
                    json.dumps(device, sort_keys=True),
                    "--server-pid",
                    str(server.pid),
                    "--limit",
                    "12",
                    "--out",
                    str(out) + ".jsonl",
                ],
                check=True,
            )
        finally:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
    print("Physical-device smoke results saved under", out.parent, "; model server stopped.")


if __name__ == "__main__":
    main()
