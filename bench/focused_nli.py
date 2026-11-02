"""Paired exploratory analysis of two released GGUF configurations, without inference."""

import argparse
import csv
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

from bench.scoring import PROMPT_VERSION, extract

LANGUAGES = ("eng", "yor")
QUANTS = ("Q8_0", "Q4_K_M")
LABELS = ("entailment", "neutral", "contradiction")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def checked_bytes(path, expected):
    if sha256(path) != expected:
        raise ValueError(f"Checksum mismatch: {path}")


def paired_items(items, expected_pairs):
    pairs = {}
    seen = set()
    for item in items:
        if item["task"] != "afrixnli" or item["language"] not in LANGUAGES:
            continue
        if item["id"] in seen:
            raise ValueError("Duplicate evaluation ID")
        seen.add(item["id"])
        group = pairs.setdefault(item["parallel_id"], {})
        if item["language"] in group:
            raise ValueError("Duplicate language in a parallel question")
        if extract("afrixnli", item["answer"]) not in LABELS:
            raise ValueError("Invalid NLI gold label")
        group[item["language"]] = item
    if len(pairs) != expected_pairs:
        raise ValueError("Unexpected number of parallel questions")
    for group in pairs.values():
        if set(group) != set(LANGUAGES):
            raise ValueError("Missing language in a parallel question")
        if group["eng"]["answer"] != group["yor"]["answer"]:
            raise ValueError("Parallel gold labels disagree")
    return pairs


def final_responses(rows, ids):
    grouped = {item_id: [] for item_id in ids}
    for row in rows:
        if row["id"] in grouped:
            grouped[row["id"]].append(row)
    final = {}
    for item_id, attempts in grouped.items():
        if not attempts or len(attempts) > 3:
            raise ValueError("Missing item or exceeded original retry limit")
        if any(row["status"] not in {"ok", "error"} for row in attempts):
            raise ValueError("Unknown response status")
        successes = [row for row in attempts if row["status"] == "ok"]
        if len(successes) > 1 or (successes and attempts[-1]["status"] != "ok"):
            raise ValueError("A successful response was resampled")
        if not successes and len(attempts) != 3:
            raise ValueError("Unfinished request failures cannot silently become final answers")
        final[item_id] = attempts[-1]
    return final, grouped


def outcome(item, row):
    if row["language"] != item["language"] or row["task"] != item["task"]:
        raise ValueError("Run identity does not match the item")
    prediction = extract("afrixnli", row.get("text", "")) if row["status"] == "ok" else None
    correct = prediction is not None and prediction == item["answer"]
    if row.get("correct") is not correct:
        raise ValueError("Stored correctness disagrees with independent rescoring")
    if row["status"] == "ok" and row.get("prediction") != prediction:
        raise ValueError("Stored prediction disagrees with independent parsing")
    if "answer_correct" in row and row["answer_correct"] is not correct:
        raise ValueError("Stored answer correctness disagrees with independent rescoring")
    return {"correct": int(correct), "prediction": prediction, "status": row["status"]}


def percentile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def contrasts(pairs, replicates, seed):
    """One sampled ID carries both languages and both quantization outcomes."""
    if not pairs or replicates < 100:
        raise ValueError("Need paired observations and at least 100 bootstrap replicates")
    differences = {
        lang: [p[f"{lang}_Q4_K_M_correct"] - p[f"{lang}_Q8_0_correct"] for p in pairs]
        for lang in LANGUAGES
    }
    n = len(pairs)
    samples = {"eng": [], "yor": [], "interaction": []}
    rng = random.Random(seed)
    for _ in range(replicates):
        indices = rng.choices(range(n), k=n)
        eng = 100 * sum(differences["eng"][i] for i in indices) / n
        yor = 100 * sum(differences["yor"][i] for i in indices) / n
        for key, value in [("eng", eng), ("yor", yor), ("interaction", yor - eng)]:
            samples[key].append(value)
    points = {lang: 100 * sum(values) / n for lang, values in differences.items()}
    points["interaction"] = points["yor"] - points["eng"]
    return {
        key: {
            "estimate_pp": points[key],
            "ci95_pp": [percentile(values, 0.025), percentile(values, 0.975)],
        }
        for key, values in samples.items()
    }


def cell_summary(language, quant, items, rows, attempts):
    n = len(items)
    gold = Counter(item["answer"] for item in items)
    predicted = Counter()
    confusion = {label: {p: 0 for p in (*LABELS, "invalid_or_error")} for label in LABELS}
    correct = invalid = failures = capped = 0
    token_counts = []
    for item in items:
        row = rows[item["id"]]
        score = outcome(item, row)
        label = score["prediction"] or "invalid_or_error"
        predicted[label] += 1
        confusion[item["answer"]][label] += 1
        correct += score["correct"]
        failures += row["status"] == "error"
        invalid += row["status"] == "ok" and score["prediction"] is None
        capped += row.get("finish_reason") == "length"
        tokens = row.get("usage", {}).get("prompt_tokens")
        if tokens is not None:
            token_counts.append(tokens)
    return {
        "language": language,
        "quantization": quant,
        "n": n,
        "correct": correct,
        "accuracy_percent": 100 * correct / n,
        "attempts": sum(len(attempts[item["id"]]) for item in items),
        "failed_attempts": sum(
            r["status"] == "error" for item in items for r in attempts[item["id"]]
        ),
        "final_request_failures": failures,
        "unparseable_successes": invalid,
        "output_cap_stops": capped,
        "accuracy_among_parseable_percent": 100 * correct / (n - invalid - failures)
        if n - invalid - failures
        else None,
        "reported_prompt_token_range": [min(token_counts), max(token_counts)]
        if token_counts
        else None,
        "gold_counts": dict(gold),
        "prediction_counts": dict(predicted),
        "confusion_gold_rows_prediction_columns": confusion,
        "class_recall_percent": {
            label: 100 * confusion[label][label] / gold[label] if gold[label] else None
            for label in LABELS
        },
        "observed_majority_label_accuracy_percent": 100 * max(gold.values()) / n,
    }


def analyse(plan, items_path):
    checked_bytes(items_path, plan["data_sha256"])
    checked_bytes("bench/scoring.py", plan["scorer_sha256"])
    checked_bytes("bench/client.py", plan["inference_client_sha256"])
    checked_bytes(plan["provenance"], plan["provenance_sha256"])
    if plan["bootstrap"]["confidence"] != 0.95:
        raise ValueError("This analysis implements 95% intervals only")
    if plan["prompt_version"] != PROMPT_VERSION:
        raise ValueError("Prompt implementation changed")
    items = read_jsonl(items_path)
    pairs = paired_items(items, plan["expected_parallel_pairs"])
    ids = {item["id"] for group in pairs.values() for item in group.values()}
    if any(
        item["revision"] != plan["dataset_revision"]
        for group in pairs.values()
        for item in group.values()
    ):
        raise ValueError("Dataset revision changed")
    finals, attempts = {}, {}
    for quant in QUANTS:
        condition = plan["conditions"][quant]
        checked_bytes(condition["run"], condition["sha256"])
        rows = read_jsonl(condition["run"])
        if len({row["run_id"] for row in rows}) != 1:
            raise ValueError("Mixed run identities")
        expected = {
            "model": condition["model"],
            "model_revision": condition["weights_sha256"],
            "items_sha256": plan["data_sha256"],
            "prompt_version": plan["prompt_version"],
            "max_tokens": plan["max_tokens"],
            "translate": False,
            "partial": False,
        }
        if any(any(row.get(key) != value for key, value in expected.items()) for row in rows):
            raise ValueError("Run controls differ from the specified analysis")
        if any("replicate" in row for row in rows):
            raise ValueError("Timing repeats are not independent accuracy data")
        finals[quant], attempts[quant] = final_responses(rows, ids)
    paired = []
    for parallel_id in sorted(pairs, key=lambda value: int(value.rsplit(":", 1)[1])):
        group = pairs[parallel_id]
        record = {"parallel_id": parallel_id, "gold": group["eng"]["answer"]}
        for language in LANGUAGES:
            item = group[language]
            for quant in QUANTS:
                row = finals[quant][item["id"]]
                score = outcome(item, row)
                for key, value in score.items():
                    record[f"{language}_{quant}_{key}"] = value
            a, b = [finals[q][item["id"]] for q in QUANTS]
            if a["status"] == b["status"] == "ok":
                if a["usage"]["prompt_tokens"] != b["usage"]["prompt_tokens"]:
                    raise ValueError("Prompt token counts changed across configurations")
                if a["request_body_bytes"] != b["request_body_bytes"]:
                    raise ValueError("Serialized request sizes changed across configurations")
        paired.append(record)
    summaries = [
        cell_summary(
            language, quant, [g[language] for g in pairs.values()], finals[quant], attempts[quant]
        )
        for language in LANGUAGES
        for quant in QUANTS
    ]
    concordance = {}
    for language in LANGUAGES:
        counts = Counter(
            (p[f"{language}_Q4_K_M_correct"], p[f"{language}_Q8_0_correct"]) for p in paired
        )
        concordance[language] = {
            "both_correct": counts[(1, 1)],
            "q4_only_correct": counts[(1, 0)],
            "q8_only_correct": counts[(0, 1)],
            "both_incorrect": counts[(0, 0)],
        }
    result = {
        "status": plan["status"],
        "question": plan["question"],
        "parallel_questions": len(paired),
        "unique_question_language_items": len(ids),
        "condition_item_outcomes": len(ids) * 2,
        "new_inference_requests": 0,
        "cells": summaries,
        "contrasts": contrasts(paired, plan["bootstrap"]["replicates"], plan["bootstrap"]["seed"]),
        "paired_correctness_concordance": concordance,
        "primary_contrast": plan["primary_contrast"],
        "bootstrap": plan["bootstrap"],
        "conditioning": "The intervals describe question variation in the recorded runs. They do not cover host changes, translation errors or differences between repeated runs. The question was narrowed after results were inspected, and configuration order was not randomised.",
        "input_hashes": {q: plan["conditions"][q]["sha256"] for q in QUANTS},
        "data_sha256": plan["data_sha256"],
        "analysis_code_sha256": sha256(Path(__file__)),
        "run_periods": {
            q: {
                "first": min(r["timestamp"] for r in finals[q].values()),
                "last": max(r["timestamp"] for r in finals[q].values()),
            }
            for q in QUANTS
        },
    }
    return result, paired


def plot(result, path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (left, right) = plt.subplots(1, 2, figsize=(10.6, 4.3), layout="constrained")
    colors = {"eng": "#24476b", "yor": "#18766e"}
    names = {"eng": "English", "yor": "Yoruba"}
    for lang in LANGUAGES:
        cells = [
            next(c for c in result["cells"] if c["language"] == lang and c["quantization"] == quant)
            for quant in QUANTS
        ]
        left.plot(
            [0, 1],
            [c["accuracy_percent"] for c in cells],
            "o-",
            label=names[lang],
            color=colors[lang],
            linewidth=2,
        )
        for x, cell in enumerate(cells):
            left.annotate(
                f"{cell['accuracy_percent']:.2f}%",
                (x, cell["accuracy_percent"]),
                xytext=(0, 9),
                textcoords="offset points",
                ha="center",
                fontsize=9,
            )
    left.axhline(
        34,
        linestyle=":",
        color="#777777",
        linewidth=1,
        label="Majority-label baseline (34%)",
    )
    left.set(
        xticks=[0, 1],
        xticklabels=QUANTS,
        xlim=(-0.3, 1.3),
        ylim=(0, 100),
        ylabel="Strict task accuracy (%)",
        title="Accuracy on 300 questions per language",
    )
    left.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), frameon=False, fontsize=8)
    labels = [
        ("eng", "English: Q4 minus Q8"),
        ("yor", "Yoruba: Q4 minus Q8"),
        ("interaction", "Yoruba change minus English change"),
    ]
    for index, (key, _) in enumerate(labels):
        value = result["contrasts"][key]
        point = value["estimate_pp"]
        lo, hi = value["ci95_pp"]
        color = colors.get(key, "#252525")
        # Percentile intervals need not contain the point estimate for every possible dataset.
        right.hlines(index, lo, hi, color=color, linewidth=2)
        right.plot(point, index, "o", color=color)
    right.axvline(0, color="#777777", linestyle="--", linewidth=1)
    right.set(
        yticks=list(range(3)),
        yticklabels=[label for _, label in labels],
        xlabel="Accuracy difference (percentage points)",
        title="Paired changes with 95% bootstrap intervals",
    )
    right.invert_yaxis()
    right.margins(y=0.35)
    for axis in (left, right):
        axis.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Qwen2.5-1.5B: Q8_0 and Q4_K_M", fontsize=13)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plan", type=Path, default=Path("report/focused-study/analysis-plan.json")
    )
    parser.add_argument("--items", type=Path, default=Path("data/prepared/items.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("report/focused-study"))
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    result, paired = analyse(plan, args.items)
    result["analysis_plan_sha256"] = sha256(args.plan)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    with (args.out / "paired-results.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(paired[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(paired)
    plot(result, args.out / "paired-analysis.png")
    print(
        json.dumps(
            {
                "parallel_questions": len(paired),
                "contrasts": result["contrasts"],
                "new_inference_requests": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
