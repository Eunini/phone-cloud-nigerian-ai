"""Paired, revision-pinned IrokoBench samples, with no test-set oversampling."""

import argparse
import ast
import hashlib
import json
import random
from pathlib import Path

from datasets import load_dataset

REVISIONS = {
    "afrimmlu": "96f247619673906ae4c321a3232afc67b98ea57e",
    "afrixnli": "e3ca06b30f3e7af2a86f6c8609ea76fee326bc56",
    "afrimgsm": "8e4268d2b94941f18f63f694cf48e4ae26fbec65",
}
LANGUAGES = ["yor", "hau", "ibo", "eng"]
NLI_LABELS = {0: "entailment", 1: "neutral", 2: "contradiction"}


def convert(task, language, index, row):
    item = {
        "id": f"{task}:{language}:{index}",
        "parallel_id": f"{task}:{index}",
        "language": language,
        "task": task,
        "revision": REVISIONS[task],
    }
    if task == "afrimmlu":
        choices = (
            ast.literal_eval(row["choices"]) if isinstance(row["choices"], str) else row["choices"]
        )
        if len(choices) != 4 or row["answer"] not in "ABCD":
            raise ValueError("Unexpected MMLU schema")
        item.update(question=row["question"], choices=choices, answer=row["answer"])
    elif task == "afrixnli":
        item.update(
            premise=row["premise"],
            hypothesis=row["hypothesis"],
            answer=NLI_LABELS[int(row["label"])],
        )
    else:
        item.update(question=row["question"], answer=str(row["answer_number"]))
    return item


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("data/prepared"))
    p.add_argument("--n", type=int, default=300)
    p.add_argument("--seed", type=int, default=2026)
    a = p.parse_args()
    if a.n < 1:
        p.error("--n must be positive")
    a.out.mkdir(parents=True, exist_ok=True)
    audit, selected = {}, []
    for task, revision in REVISIONS.items():
        datasets = {
            lang: load_dataset(f"masakhane/{task}", lang, split="test", revision=revision)
            for lang in LANGUAGES
        }
        sizes = {lang: len(ds) for lang, ds in datasets.items()}
        if len(set(sizes.values())) != 1:
            raise ValueError(f"Cannot assume parallel row indices: {sizes}")
        indices = sorted(
            random.Random(a.seed).sample(range(min(sizes.values())), min(a.n, min(sizes.values())))
        )
        audit[task] = {
            "dataset": f"masakhane/{task}",
            "revision": revision,
            "available": sizes,
            "selected_per_language": len(indices),
            "selection": "same seeded row indices across languages; no replacement",
        }
        for lang, ds in datasets.items():
            selected.extend(convert(task, lang, i, ds[i]) for i in indices)
    content = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in selected)
    paired = {}
    for row in selected:
        prior = paired.setdefault(row["parallel_id"], row["answer"])
        if prior != row["answer"]:
            raise ValueError(
                "Parallel gold answers disagree; review source alignment before pairing"
            )
    (a.out / "items.jsonl").write_text(content)
    (a.out / "audit.json").write_text(
        json.dumps(
            {
                "seed": a.seed,
                "datasets": audit,
                "n": len(selected),
                "items_sha256": hashlib.sha256(content.encode()).hexdigest(),
            },
            indent=2,
        )
    )
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
