"""Post-hoc exact-choice diagnostic; never replaces the predeclared strict score."""

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path


def normalized(text):
    return " ".join(unicodedata.normalize("NFC", text).casefold().split()).rstrip(".")


def exact_choice(item, output):
    match = re.fullmatch(r"\s*([A-Da-d])[.)]\s+(.+?)\s*", output, re.DOTALL)
    if match:
        label = match[1].upper()
        if normalized(match[2]) == normalized(item["choices"]["ABCD".index(label)]):
            return label
        return None
    candidates = [
        "ABCD"[i]
        for i, choice in enumerate(item["choices"])
        if normalized(choice) == normalized(output)
    ]
    return candidates[0] if len(candidates) == 1 else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--items", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if (
        hashlib.sha256(a.items.read_bytes()).hexdigest()
        != "c9bdac81650e6c4b9c3c6aaf36730df05fe975628149643248c4da946dc3f07f"
    ):
        raise ValueError("Use the original audited question selection")
    items = {r["id"]: r for r in map(json.loads, a.items.read_text().splitlines())}
    rows = list({r["id"]: r for r in map(json.loads, a.run.read_text().splitlines())}.values())
    groups = []
    for language in ("eng", "yor", "hau", "ibo"):
        group = [r for r in rows if r["language"] == language and r["task"] == "afrimmlu"]
        recovered = [
            r
            for r in group
            if r.get("prediction") is None
            and r["status"] == "ok"
            and exact_choice(items[r["id"]], r["text"]) is not None
        ]
        additional = sum(
            exact_choice(items[r["id"]], r["text"]) == items[r["id"]]["answer"] for r in recovered
        )
        strict = sum(r.get("correct", False) for r in group)
        groups.append(
            {
                "language": language,
                "n": len(group),
                "strict_correct": strict,
                "strict_parseable": sum(r.get("prediction") is not None for r in group),
                "exact_choice_recoverable_outputs": len(recovered),
                "additional_correct": additional,
                "strict_accuracy": strict / len(group),
                "post_hoc_exact_choice_accuracy": (strict + additional) / len(group),
            }
        )
    result = {
        "status": "post-hoc diagnostic",
        "run_sha256": hashlib.sha256(a.run.read_bytes()).hexdigest(),
        "policy": "Recover only an exact option string, optionally prefixed by its matching letter and punctuation; never extract arbitrary letters from an explanation",
        "primary_scores_changed": False,
        "new_model_requests": 0,
        "interpretation": "Separates some output-format failures from wrong content; not a preregistered performance result or complete semantic evaluation",
        "groups": groups,
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
