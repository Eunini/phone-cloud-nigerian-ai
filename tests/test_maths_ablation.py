import random

import pytest

from bench.maths_ablation import relaxed_number, select


@pytest.mark.parametrize("response, expected", [
    ("We can work this out.\nThere are 42 books.", "42"),
    ("The answer is **1,200**.", "1.2E+3"),
    ("FINAL: -2.5", "-2.5"),
    ("I got 10 or 42.", None),
    ("20 + 22 = 42", None),
    ("The answer is 1/2.", None),
    ("I cannot solve this.", None),
])
def test_relaxed_extraction_never_searches_for_the_gold(response, expected):
    assert relaxed_number(response) == expected


def test_fifty_question_selection_is_fixed_and_nearly_balanced():
    rows = [{"task": "afrimgsm", "parallel_id": f"p{i}", "language": lang,
             "id": f"{i}:{lang}"} for i in range(20) for lang in ["eng", "yor", "hau", "ibo"]]
    first = select(rows)
    random.Random(9).shuffle(rows)
    assert first == select(rows)
    assert len(first) == len({r["id"] for r in first}) == 50
    assert sum(r["language"] == "eng" for r in first) == 13
    assert sum(r["language"] == "hau" for r in first) == 12
