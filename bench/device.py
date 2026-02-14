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
        "memory_total_bytes": psutil.virtual_memory().total,
        "memory_available_bytes_at_setup": psutil.virtual_memory().available,
        "disk_free_bytes_at_setup": shutil.disk_usage(".").free,
        "python": platform.python_version(),
    }
    if shutil.which("getprop"):
        keys = [
            "ro.product.manufacturer",
            "ro.product.model",
            "ro.soc.model",
            "ro.soc.manufacturer",
            "ro.build.version.release",
            "ro.product.cpu.abilist",
        ]
        result["android"] = {
            key: subprocess.check_output(["getprop", key], text=True).strip() for key in keys
        }
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
