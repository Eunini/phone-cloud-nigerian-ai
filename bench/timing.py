"""Choose timing repetitions before examining model outputs; accuracy uses the full set."""

import argparse
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--items", type=Path, default=Path("data/prepared/items.jsonl"))
    p.add_argument("--out", type=Path, default=Path("data/prepared/timing120.jsonl"))
    a = p.parse_args()
    groups = defaultdict(list)
    for line in a.items.read_text().splitlines():
        row = json.loads(line)
        groups[(row["language"], row["task"])].append(row)
    if len(groups) != 12 or min(map(len, groups.values())) < 10:
        raise ValueError("Expected all twelve audited language/task groups")
    rng = random.Random(2026)
    selected = []
    for key in sorted(groups):
        candidates = sorted(groups[key], key=lambda r: r["id"])
        rng.shuffle(candidates)
        selected += candidates[:10]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in selected))
    print(
        json.dumps(
            {
                "n": len(selected),
                "per_group": 10,
                "seed": 2026,
                "sha256": hashlib.sha256(a.out.read_bytes()).hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    main()
