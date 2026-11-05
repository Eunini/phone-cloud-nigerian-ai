"""Verify private maths observations and publish aggregate counts only."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from bench.maths_ablation import CONDITIONS, relaxed_number, sha, summarize
from bench.scoring import correct, extract


def verified_report(root):
    plan = json.loads((root / "report/maths-ablation/plan.json").read_text())
    source = root / "data/prepared/items.jsonl"
    if sha(source) != plan["source_sha256"] or sha(root / "bench/maths_ablation.py") != plan["module_sha256"]:
        raise ValueError("Source questions or frozen generation/scoring module changed")
    items = {r["id"]: r for r in map(json.loads, source.read_text().splitlines())}
    private = root / "runs/private/maths-ablation-v1"
    records = [json.loads(x) for x in (private / "responses.jsonl").read_text().splitlines()]
    seen = set()
    for row in records:
        key = row["id"], row["style"], row["max_tokens"]
        if key in seen or row["id"] not in plan["selected_ids"] or (row["style"], row["max_tokens"]) not in CONDITIONS:
            raise ValueError("Unexpected or repeated experimental case")
        seen.add(key)
        if row["status"] == "ok":
            item = items[row["id"]]
            predicted = relaxed_number(row["text"])
            if row["strict_correct"] != correct(item, row["text"]):
                raise ValueError("Strict score does not reproduce")
            if row["relaxed_prediction"] != predicted or row["relaxed_correct"] != (
                predicted is not None and predicted == extract("afrimgsm", item["answer"])
            ):
                raise ValueError("Relaxed score does not reproduce")
    shutdown = json.loads((root / "report/maths-ablation/shutdown.json").read_text())
    if shutdown.get("server_stopped") is not True:
        raise ValueError("Worker has not confirmed model-server shutdown")
    result = summarize(records)
    result.update(finalized_at_utc=datetime.now(timezone.utc).isoformat(),
                  verified_against_private_journal=True, server_stopped=True,
                  private_journal_sha256=sha(private / "responses.jsonl"),
                  language_inference="12 or 13 cases per language; exploratory pilot, not a reliable language ranking",
                  human_semantic_review_complete=False)
    report = root / "report/maths-ablation"
    (report / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = ["# Maths prompt and length pilot", "", "Status: " + result["status"] + ".",
             "", "All counts are out of 50 planned questions per condition.", "",
             "| Instructions | Output limit | Completed | Cutoffs | Strict correct | Relaxed correct | Relaxed correct, uncapped |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for group in result["groups"]:
        lines.append("| " + " | ".join(str(group[k]) for k in [
            "style", "max_tokens", "completed", "cutoffs", "strict_correct", "relaxed_correct",
            "relaxed_correct_uncapped"]) + " |")
    lines += ["", "The original published benchmark scores remain unchanged. Compare the same",
              "scoring rule across the four conditions; changing the prompt and scoring rule",
              "at the same time does not isolate a prompt effect. The relaxed parser is a",
              "conservative numeric diagnostic, not full semantic judgment. Unparseable",
              "answers and capped responses need review; they do not establish lack of",
              "understanding. No independent human semantic review is claimed.", "",
              "This is a small exploratory sample from previously evaluated items. It does",
              "not establish general language ability, a statistically reliable improvement",
              "or a new primary score. See [the frozen plan](plan.json) and [method](README.md).", ""]
    (report / "results.md").write_text("\n".join(lines))
    # Human readers receive neither the automatic labels nor the treatment code.
    import hashlib
    import random

    shuffled = [r for r in records if r["status"] == "ok"]
    random.Random(20261105).shuffle(shuffled)
    packet = private / "blinded-answer-review.csv"
    with packet.open("w", newline="") as stream:
        packet.chmod(0o600)
        fields = ["review_id", "language", "question", "response", "final_answer", "correct", "reviewer", "notes"]
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        for row in shuffled:
            writer.writerow({"review_id": hashlib.sha256(json.dumps([
                row["id"], row["style"], row["max_tokens"]]).encode()).hexdigest()[:16],
                "language": row["language"], "question": items[row["id"]]["question"],
                "response": row["text"]})
    return result


if __name__ == "__main__":
    result = verified_report(Path(__file__).resolve().parents[1])
    print(json.dumps({"status": result["status"], "verified_against_private_journal": True}))
