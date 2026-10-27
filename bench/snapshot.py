"""Create an immutable complete-line snapshot without changing a running study."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def snapshot(source, target):
    raw = Path(source).read_bytes()
    end = raw.rfind(b"\n") + 1
    complete = raw[:end]
    rows = [json.loads(line) for line in complete.splitlines()]
    if not rows or len({r["run_id"] for r in rows}) != 1:
        raise ValueError("Snapshot needs a nonempty, single-identity valid run")
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(complete)
    receipt = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "snapshot": str(target),
        "source_bytes_observed": len(raw),
        "snapshot_bytes": len(complete),
        "unflushed_tail_bytes_excluded": len(raw) - end,
        "source_sha256_at_read": hashlib.sha256(raw).hexdigest(),
        "snapshot_sha256": hashlib.sha256(complete).hexdigest(),
        "records": len(rows),
        "unique_items": len({r["id"] for r in rows}),
        "successful_unique_items": len({r["id"] for r in rows if r["status"] == "ok"}),
        "scope": "Completed JSONL prefix only; source file is never altered",
    }
    target.with_suffix(".snapshot.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path)
    p.add_argument("target", type=Path)
    a = p.parse_args()
    print(json.dumps(snapshot(a.source, a.target), indent=2))
