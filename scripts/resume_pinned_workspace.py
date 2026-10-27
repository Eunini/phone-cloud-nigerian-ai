"""Record a TCP port-guard fix while retaining the measured evaluator at its pin."""

import argparse
import hashlib
import json
import os
import runpy
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PIN = "c75b734e48defc6f19cc0c2d32bd8a944f6b0595"


class ReusablePortCheckSocket(socket.socket):
    def bind(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6) and self.type == socket.SOCK_STREAM:
            self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return super().bind(address)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    a, forwarded = p.parse_known_args()
    source = a.source.resolve(strict=True)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    if revision != PIN:
        raise ValueError("Resume only the original pinned source")
    hashes = {}
    for name in (
        "bench/run.py",
        "bench/client.py",
        "bench/scoring.py",
        "bench/translate.py",
        "bench/timing.py",
        "bench/workspace.py",
        "configs/models.json",
    ):
        original = subprocess.check_output(["git", "show", PIN + ":" + name], cwd=source)
        current = (source / name).read_bytes()
        if current != original:
            raise ValueError("Pinned evaluator/controller source changed: " + name)
        hashes[name] = hashlib.sha256(current).hexdigest()
    receipt = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_source_commit": PIN,
        "port_guard_wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "verified_core_sources_sha256": hashes,
        "change": "Controller port checks allow TCP TIME_WAIT reuse; a live listening service still blocks binding",
        "inference_changed": False,
        "existing_predictions_rewritten": False,
    }
    a.receipt.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with a.receipt.open("a") as stream:
        stream.write(json.dumps(receipt, sort_keys=True) + "\n")
    a.receipt.chmod(0o600)
    # Only this controller process is patched. Its evaluator and model-server
    # children start fresh interpreters/binaries with the original request code.
    socket.socket = ReusablePortCheckSocket
    os.chdir(source)
    sys.path.insert(0, str(source))
    sys.argv = ["bench.workspace", *forwarded]
    runpy.run_module("bench.workspace", run_name="__main__")


if __name__ == "__main__":
    main()
