"""Build an offline evaluator bundle; prepare datasets on the development host."""

import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--items", type=Path, default=Path("data/prepared/items.jsonl"))
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    rows = [json.loads(x) for x in a.items.read_text().splitlines() if x.strip()]
    if len(rows) != 3400 or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Prepare the audited 3,400 unique items before building the phone bundle")
    root = Path(__file__).absolute().parents[1]
    sources = [
        "bench/__init__.py",
        "bench/run.py",
        "bench/client.py",
        "bench/scoring.py",
        "bench/translate.py",
        "bench/timing.py",
        "bench/device.py",
        "bench/phone_smoke.py",
        "scripts/termux.sh",
        "configs/models.json",
        "LICENSE",
        "DATA-NOTICE.md",
        "licenses/Apache-2.0.txt",
        "licenses/dataset-cards/afrimmlu.md",
        "licenses/dataset-cards/afrixnli.md",
        "licenses/dataset-cards/afrimgsm.md",
        "report/data-audit.json",
        "report/android-guide.md",
    ]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    hashes = {}
    with tarfile.open(a.out, "w:gz") as archive:
        for name in sources + ["data/prepared/items.jsonl"]:
            data = (
                a.items.read_bytes()
                if name == "data/prepared/items.jsonl"
                else (root / name).read_bytes()
            )
            hashes[name] = hashlib.sha256(data).hexdigest()
            info = tarfile.TarInfo("afri-phone/" + name)
            info.mode = 0o755 if name.endswith(".sh") else 0o644
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        body = (json.dumps(hashes, indent=2) + "\n").encode()
        info = tarfile.TarInfo("afri-phone/bundle-sha256.json")
        info.size = len(body)
        info.mode = 0o644
        archive.addfile(info, io.BytesIO(body))
    print(
        json.dumps(
            {
                "path": str(a.out),
                "bytes": a.out.stat().st_size,
                "sha256": hashlib.sha256(a.out.read_bytes()).hexdigest(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
