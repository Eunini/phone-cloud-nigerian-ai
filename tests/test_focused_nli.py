from copy import deepcopy

import pytest

from bench.focused_nli import (
    checked_bytes,
    contrasts,
    final_responses,
    outcome,
    paired_items,
    percentile,
)


def item(language, index=0, answer="neutral"):
    return {
        "id": f"afrixnli:{language}:{index}",
        "parallel_id": f"afrixnli:{index}",
        "task": "afrixnli",
        "language": language,
        "answer": answer,
    }


def response(question, status="ok", answer="neutral"):
    return {
        "id": question["id"],
        "language": question["language"],
        "task": "afrixnli",
        "status": status,
        "text": f"FINAL: {answer}" if status == "ok" else "",
        "prediction": answer if status == "ok" else None,
        "correct": status == "ok" and question["answer"] == answer,
    }


def test_pairing_requires_both_languages_same_gold_and_unique_ids():
    questions = [item("eng"), item("yor")]
    assert len(paired_items(questions, 1)) == 1
    for broken in [
        questions[:1],
        questions + [item("yor")],
        [item("eng"), item("yor", answer="contradiction")],
    ]:
        with pytest.raises(ValueError):
            paired_items(broken, 1)
    with pytest.raises(ValueError, match="number"):
        paired_items(questions, 2)


def test_retries_preserve_one_outcome_and_cannot_resample_success():
    question = item("eng")
    failed, good = response(question, "error"), response(question)
    final, attempts = final_responses([failed, good], {question["id"]})
    assert final[question["id"]] == good and len(attempts[question["id"]]) == 2
    final, _ = final_responses([failed] * 3, {question["id"]})
    assert final[question["id"]]["status"] == "error"
    for broken in [[], [failed], [good, good], [good, failed], [failed] * 4]:
        with pytest.raises(ValueError):
            final_responses(broken, {question["id"]})


def test_rescoring_rejects_corrupted_cached_scores_and_predictions():
    question = item("eng")
    good = response(question)
    assert outcome(question, good)["correct"] == 1
    for replacement in [
        {"correct": False},
        {"prediction": "contradiction"},
        {"language": "yor"},
        {"answer_correct": False},
    ]:
        with pytest.raises(ValueError):
            outcome(question, {**good, **replacement})
    bad_format = {
        **good,
        "text": "It could be neutral or entailment.",
        "prediction": None,
        "correct": False,
    }
    assert outcome(question, bad_format)["prediction"] is None


def test_bootstrap_keeps_the_four_question_outcomes_together():
    # Both languages change identically on every question. Resampling languages
    # independently would incorrectly introduce uncertainty into the interaction.
    observations = []
    for i in range(20):
        observations.append(
            {
                f"{lang}_{quant}_correct": int((i % 2 == 0) == (quant == "Q4_K_M"))
                for lang in ["eng", "yor"]
                for quant in ["Q4_K_M", "Q8_0"]
            }
        )
    result = contrasts(observations, 500, 2026)
    assert result["interaction"] == {"estimate_pp": 0, "ci95_pp": [0, 0]}
    assert result["eng"] == result["yor"]
    assert result == contrasts(observations, 500, 2026)


def test_contrast_direction_uses_q4_minus_q8_then_yoruba_minus_english():
    question = {
        "eng_Q4_K_M_correct": 1,
        "eng_Q8_0_correct": 1,
        "yor_Q4_K_M_correct": 0,
        "yor_Q8_0_correct": 1,
    }
    result = contrasts([deepcopy(question)] * 5, 100, 2026)
    assert result["eng"]["estimate_pp"] == 0
    assert result["yor"]["estimate_pp"] == -100
    assert result["interaction"] == {"estimate_pp": -100, "ci95_pp": [-100, -100]}


def test_linear_percentiles_and_minimum_bootstrap_size():
    assert percentile([0, 10], 0.25) == 2.5
    with pytest.raises(ValueError):
        contrasts([], 100, 2026)
    with pytest.raises(ValueError):
        contrasts([{}], 10, 2026)


def test_checksum_guard_rejects_modified_inputs(tmp_path):
    path = tmp_path / "run.jsonl"
    path.write_text("an altered result")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        checked_bytes(path, "0" * 64)
