"""Collect non-identifying hardware metadata; excludes serials, accounts and network IDs."""

import argparse
import json
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import psutil


def metadata():
    result = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "logical_cpus": psutil.cpu_count(),
        "disk_free_bytes_at_setup": shutil.disk_usage(".").free,
        "python": platform.python_version(),
    }
    try:
        memory = psutil.virtual_memory()
        result.update(
            memory_total_bytes=memory.total, memory_available_bytes_at_setup=memory.available
        )
    except (OSError, NotImplementedError, psutil.AccessDenied) as error:
        result.update(
            memory_total_bytes=None,
            memory_available_bytes_at_setup=None,
            memory_metadata_error=type(error).__name__,
        )
    if shutil.which("getprop"):
        keys = [
            "ro.product.manufacturer",
            "ro.product.model",
            "ro.soc.model",
            "ro.soc.manufacturer",
            "ro.build.version.release",
            "ro.product.cpu.abilist",
        ]
        result["android"] = {}
        for key in keys:
            response = subprocess.run(["getprop", key], capture_output=True, text=True)
            result["android"][key] = (
                response.stdout.strip() or None if response.returncode == 0 else None
            )
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("report/device.json"))
    a = p.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    value = metadata()
    a.out.write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps(value, indent=2))


if __name__ == "__main__":
    main()
