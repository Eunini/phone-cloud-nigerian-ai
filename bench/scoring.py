import re
from decimal import Decimal, InvalidOperation

PROMPT_VERSION = "fixed-en-instructions-v1"


def prompt(item):
    task = item["task"]
    if task == "afrimmlu":
        choices = "\n".join(
            f"{letter}. {value}" for letter, value in zip("ABCD", item["choices"], strict=True)
        )
        return (
            "Answer the multiple-choice question. Return only FINAL: A, FINAL: B, "
            f"FINAL: C, or FINAL: D.\n\n{item['question']}\n{choices}"
        )
    if task == "afrixnli":
        return (
            "Classify the hypothesis relative to the premise. Return only FINAL: entailment, "
            "FINAL: neutral, or FINAL: contradiction.\n\n"
            f"Premise: {item['premise']}\nHypothesis: {item['hypothesis']}"
        )
    if task == "afrimgsm":
        return (
            "Solve the math problem. You may reason briefly, then put the numeric answer "
            f"alone on the final line as FINAL: <number>.\n\n{item['question']}"
        )
    raise ValueError(task)


def extract(task, output):
    # Repeated/ambiguous final markers are invalid rather than cherry-picked.
    matches = re.findall(r"(?im)^\s*FINAL:\s*([^\n]+)\s*$", output)
    if len(matches) > 1:
        return None
    answer = matches[0].strip() if matches else output.strip()
    if task == "afrimmlu":
        return answer.upper() if re.fullmatch(r"[A-Da-d]", answer) else None
    if task == "afrixnli":
        answer = answer.casefold()
        return answer if answer in {"entailment", "neutral", "contradiction"} else None
    answer = answer.replace("−", "-")
    # Thousands separators are accepted only when well formed; no units or trailing explanation.
    if not re.fullmatch(r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", answer):
        return None
    try:
        return str(Decimal(answer.replace(",", "")).normalize())
    except InvalidOperation:
        return None


def correct(item, output):
    prediction = extract(item["task"], output)
    gold = extract(item["task"], item["answer"])
    if gold is None:
        raise ValueError("Invalid gold answer")
    return prediction is not None and prediction == gold
