from bench.format_diagnostic import exact_choice


def test_only_an_exact_choice_can_be_recovered_from_format_failure():
    item = {"choices": ["seven", "eight", "nine", "ten"]}
    assert exact_choice(item, "A. seven") == "A"
    assert exact_choice(item, "SEVEN.") == "A"
    assert exact_choice(item, "A. seven, because I think it is right") is None
    assert exact_choice(item, "A. eight") is None
    assert exact_choice(item, "A. seven\nB. eight") is None


def test_ambiguous_exact_choice_text_is_not_assigned_a_label():
    assert exact_choice({"choices": ["same", "same", "other", "another"]}, "same") is None
