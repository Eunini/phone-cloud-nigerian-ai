import json

import pytest

from bench.maths_ablation import sha
from bench.maths_report import verified_report


def private_fixture(root):
    for folder in ["data/prepared", "bench", "report/maths-ablation", "runs/private/maths-ablation-v1"]:
        (root / folder).mkdir(parents=True)
    source = root / "data/prepared/items.jsonl"
    source.write_text(json.dumps({"id": "one", "task": "afrimgsm", "language": "eng",
                                  "question": "PRIVATE-QUESTION", "answer": "42"}) + "\n")
    module = root / "bench/maths_ablation.py"
    module.write_text("test source fixture\n")
    plan = {"source_sha256": sha(source), "module_sha256": sha(module), "selected_ids": ["one"]}
    (root / "report/maths-ablation/plan.json").write_text(json.dumps(plan))
    record = {"id": "one", "style": "freeform", "max_tokens": 1024, "language": "eng",
              "text": "PRIVATE-RESPONSE 42", "status": "ok", "strict_correct": False,
              "strict_prediction": None, "relaxed_prediction": "42", "relaxed_correct": True,
              "finish_reason": "stop"}
    journal = root / "runs/private/maths-ablation-v1/responses.jsonl"
    journal.write_text(json.dumps(record) + "\n")
    (root / "report/maths-ablation/shutdown.json").write_text('{"server_stopped":true}')
    return journal


def test_report_never_exports_question_or_response_text(tmp_path):
    private_fixture(tmp_path)
    result = verified_report(tmp_path)
    assert result["status"] == "partial" and result["verified_against_private_journal"]
    for name in ["results.json", "results.md"]:
        assert "PRIVATE-" not in (tmp_path / "report/maths-ablation" / name).read_text()
    packet = (tmp_path / "runs/private/maths-ablation-v1/blinded-answer-review.csv").read_text()
    assert "PRIVATE-QUESTION" in packet and "PRIVATE-RESPONSE" in packet


def test_duplicate_observations_are_rejected_before_publication(tmp_path):
    journal = private_fixture(tmp_path)
    journal.write_text(journal.read_text() * 2)
    with pytest.raises(ValueError, match="repeated experimental"):
        verified_report(tmp_path)
