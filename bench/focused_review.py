"""Build a concise review note from the frozen paired analysis, without inference."""

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape


def interval(value):
    lo, hi = value["ci95_pp"]
    return f"{value['estimate_pp']:+.2f} pp [{lo:+.2f}, {hi:+.2f}]"


def markdown(result):
    names = {"eng": "English", "yor": "Yoruba"}
    eng = result["paired_correctness_concordance"]["eng"]
    yor = result["paired_correctness_concordance"]["yor"]
    lines = [
        "# Results",
        "",
        "Inioluwa Atanda",
        "",
        "2 November 2026",
        "",
        "I compared Q4_K_M and Q8_0 versions of Qwen2.5-1.5B-Instruct on 300 matched "
        "English and Yoruba AfriXNLI questions. This is a reanalysis of existing answers. "
        "I chose the narrower question after examining the broader benchmark results.",
        "",
        "## Accuracy",
        "",
        "| Input language | Configuration | Correct / 300 | Accuracy | Failed attempts |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for cell in result["cells"]:
        lines.append(
            f"| {names[cell['language']]} | {cell['quantization']} | {cell['correct']} / "
            f"{cell['n']} | {cell['accuracy_percent']:.2f}% | {cell['failed_attempts']} |"
        )
    lines += [
        "",
        "For each language, I subtracted Q8 accuracy from Q4 accuracy. I then "
        "subtracted the English change from the Yoruba change. The estimated difference "
        f"is **{interval(result['contrasts']['interaction'])}**. The paired 95% bootstrap "
        "interval includes zero, so I cannot conclude that Yoruba had a greater "
        "compression penalty. This also does not show that the configurations are equivalent.",
        "",
        "| Comparison | Estimate and 95% bootstrap interval |",
        "| --- | --- |",
    ]
    for key, label in [
        ("eng", "English: Q4 minus Q8"),
        ("yor", "Yoruba: Q4 minus Q8"),
        ("interaction", "Yoruba change minus English change"),
    ]:
        lines.append(f"| {label} | {interval(result['contrasts'][key])} |")
    lines += [
        "",
        "![Accuracy and paired differences](paired-analysis.png)",
        "",
        f"English has {eng['q4_only_correct']} questions answered correctly only by Q4 and "
        f"{eng['q8_only_correct']} only by Q8. The corresponding Yoruba counts are "
        f"{yor['q4_only_correct']} and {yor['q8_only_correct']}. Keeping the outcomes paired "
        "shows which questions changed, even when the overall accuracy stayed the same.",
        "",
        "## Neutral-class errors",
        "",
        "| Language | Configuration | Entailment recall | Neutral recall | Contradiction recall |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for cell in result["cells"]:
        recall = cell["class_recall_percent"]
        lines.append(
            f"| {names[cell['language']]} | {cell['quantization']} | "
            f"{recall['entailment']:.2f}% | {recall['neutral']:.2f}% | "
            f"{recall['contradiction']:.2f}% |"
        )
    lines += [
        "",
        "Neither Yoruba configuration predicts neutral. English neutral recall is "
        "poor too. Each language has 99 entailment, 102 neutral and 99 contradiction "
        "reference labels. Always choosing the most common label would score 34% on "
        "this sample. The Yoruba scores are close to that baseline, and most Yoruba "
        "predictions are entailment. This limits what I can learn about quantization "
        "from this model and task.",
        "",
        "I have not established whether the cause is model capability, the English "
        "instructions, the benchmark translations or something else. I kept the "
        "original prompt and answer parser throughout this analysis.",
        "",
        "## Answer format, token limits and failed requests",
        "",
        "The scorer can read all 1,200 final responses, and none stops at the output "
        "token limit. One English Q8 request failed before a successful retry. That "
        "gives 1,201 attempts for 1,200 final responses, grouped into 300 question "
        "pairs. The failed attempt remains in the source log. Unreadable answers "
        "and output limits therefore do not explain these four accuracy values.",
        "",
        "Reported prompt lengths are 72 to 124 tokens for English and 92 to 281 for "
        "Yoruba, with the same counts in both configurations. Equal output limits "
        "do not make the input token counts equal. Instructions and answer labels "
        "are in English; the premise and hypothesis are in the assigned language.",
        "",
        "## What the results can establish",
        "",
        "The two configurations ran one after the other on different dates on a "
        "shared host. The bootstrap describes variation across questions in those "
        "recorded runs. It does not cover changes in host activity or differences "
        "between repeated runs. I also chose this narrower question after examining "
        "the broader results.",
        "",
        "Both model files come from the same pinned official GGUF release, but I "
        "do not have the full record of the starting weights, conversion and "
        "calibration. Q4_K_M and Q8_0 use different recipes, and Q8_0 is compressed "
        "too. The comparison cannot isolate the effect of bit width. The AfriXNLI "
        "translations have not received an independent native-speaker audit in "
        "this study.",
        "",
        "## Before a confirmation run",
        "",
        "I have listed the other 300 parallel questions from the same benchmark. "
        "They do not overlap with the questions analysed here. I have not run "
        "confirmation inference on them. Before doing so, I would agree the block "
        "order and repeated subset, use a reserved host, record how both model "
        "files were produced and arrange a translation review.",
        "",
        "The original observations and broader protocol are unchanged. This "
        "revision changes the question and analysis, rather than adding a new "
        "experiment.",
        "",
        "## Data and code",
        "",
        "See the [protocol](protocol.md), [analysis settings](analysis-plan.json), "
        "[runtime records](provenance.json), [confirmation proposal](confirmation-plan.json) "
        "and [paired outcomes](paired-results.csv). From the repository root, run "
        "`python -m bench.focused_nli` followed by `python -m bench.focused_review`. "
        "Neither command sends requests to a model.",
    ]
    return "\n".join(lines) + "\n"


def render_pdf(result, folder, font_dir):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        Image,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    pdfmetrics.registerFont(TTFont("Review", str(font_dir / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("ReviewBold", str(font_dir / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily("Review", normal="Review", bold="ReviewBold")
    body = ParagraphStyle("body", fontName="Review", fontSize=9, leading=13, spaceAfter=9)
    title = ParagraphStyle(
        "title",
        parent=body,
        fontName="ReviewBold",
        fontSize=20,
        leading=25,
        textColor=colors.HexColor("#153c48"),
        spaceAfter=14,
    )
    heading = ParagraphStyle(
        "heading",
        parent=body,
        fontName="ReviewBold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#18766e"),
        spaceBefore=9,
    )
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=11)
    story = []

    def p(text, style=body):
        story.append(Paragraph(text, style))

    def table(rows, widths):
        data = [[Paragraph(escape(str(value)), small) for value in row] for row in rows]
        value = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
        value.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7f1ed")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#18766e")),
                ]
            )
        )
        story.extend([value, Spacer(1, 10)])

    p("Q4 and Q8 accuracy<br/>in Yoruba and English", title)
    p(
        "<b>Inioluwa Atanda</b><br/>2 November 2026<br/>Exploratory analysis. Not preregistered or peer reviewed.",
        small,
    )
    p("Research question", heading)
    p(
        "Does the change in AfriXNLI accuracy from Q8_0 to Q4_K_M differ between Yoruba and English for Qwen2.5-1.5B-Instruct?"
    )
    p(
        "I compare two published GGUF versions of Qwen2.5-1.5B-Instruct on AfriXNLI. I chose this narrower question after examining the wider benchmark results. This note uses existing answers. I have not collected new model responses for it."
    )
    table(
        [
            ["Input language", "Q8_0", "Q4_K_M"],
            ["English", "300 questions", "Same 300 questions"],
            ["Yoruba", "300 parallel translations", "Same 300 translations"],
        ],
        [90, 200, 209],
    )
    p("Method", heading)
    p(
        "For each language, I subtract Q8 accuracy from Q4 accuracy. I then subtract the English change from the Yoruba change. A negative result would mean a worse change for Yoruba. Each question has four related outcomes, so the analysis keeps 300 question pairs together."
    )
    p(
        "Both model files come from the same version of the official GGUF release. The records specify the same workspace, runtime binary, two-thread CPU setup, 2,048-token context, English instructions and labels, greedy decoding, seed, 128-token output limit and answer scorer. I also check that request sizes and prompt-token counts agree between configurations for each item."
    )
    p(
        "I parse and score the selected answers again, check them against the stored results and retain request failures. I reject missing outcomes and repeated successful responses. The uncertainty estimates use 10,000 bootstrap samples, seed 20261102, with all four outcomes for a question sampled together. I report 95% percentile intervals for these recorded runs."
    )
    p("Limits of the existing runs", heading)
    p(
        "The configurations ran on different dates on a shared host, and their order was not randomised. I do not have the full history of the original weights, conversion and calibration. Q8_0 is also compressed, and the recipes differ as well as nominal precision. These records cannot isolate the effect of bit width."
    )
    p(
        "Other tasks, languages, models, providers, translation pipelines and timing repeats are outside this analysis. I do not use the results to draw conclusions about serving cost, latency, phones or production reliability."
    )

    story.append(PageBreak())
    p("Accuracy and paired differences", title)
    value = result["contrasts"]["interaction"]
    p(
        "<b>Main comparison: "
        + interval(value)
        + ".</b> The 95% bootstrap interval includes zero. I cannot conclude that Yoruba had a greater compression penalty. This does not show that the configurations are equivalent or establish a general effect of bit width."
    )
    rows = [["Language", "Configuration", "Correct / 300", "Accuracy"]]
    for cell in result["cells"]:
        rows.append(
            [
                {"eng": "English", "yor": "Yoruba"}[cell["language"]],
                cell["quantization"],
                str(cell["correct"]),
                f"{cell['accuracy_percent']:.2f}%",
            ]
        )
    table(rows, [85, 135, 140, 139])
    rows = [["Paired contrast", "Estimate [95% bootstrap interval]"]]
    for key, name in [
        ("eng", "English: Q4 minus Q8"),
        ("yor", "Yoruba: Q4 minus Q8"),
        ("interaction", "Yoruba change minus English change"),
    ]:
        rows.append([name, interval(result["contrasts"][key])])
    table(rows, [270, 229])
    story.append(Image(str(folder / "paired-analysis.png"), width=499, height=202))
    p(
        "The English configurations have the same overall accuracy, but four questions are answered correctly only by Q4 and four only by Q8. The corresponding Yoruba counts are six and one. The bootstrap keeps the related answers together when sampling questions.",
        small,
    )
    p(
        "The scorer can read all 1,200 final responses, and none stops at the output token limit. One English Q8 request failed before a successful retry. That attempt remains in the source log. Answer format and output limits therefore do not explain these accuracy values."
    )

    story.append(PageBreak())
    p("Errors and remaining checks", title)
    p("Neutral-class results", heading)
    table(
        [
            ["Language", "Configuration", "Neutral recall"],
            *[
                [
                    {"eng": "English", "yor": "Yoruba"}[cell["language"]],
                    cell["quantization"],
                    f"{cell['class_recall_percent']['neutral']:.2f}%",
                ]
                for cell in result["cells"]
            ],
        ],
        [110, 190, 199],
    )
    p(
        "Neither Yoruba configuration predicts neutral. English neutral recall is poor too. Each language has 99 entailment, 102 neutral and 99 contradiction reference labels. Always choosing the most common label would score 34% on this sample. Most Yoruba predictions are entailment. I have not established whether the cause is model capability, prompting, translations or something else."
    )
    p(
        "Reported prompt lengths are 72 to 124 tokens in English and 92 to 281 in Yoruba. Instructions and labels are in English; the premise and hypothesis are in the assigned language. I kept the original prompt and answer parser."
    )
    p("Before a confirmation run", heading)
    p(
        "The intervals describe variation across questions in the existing runs. They do not cover changes in host activity, differences between repeated runs, translation errors or the decision to narrow the question after seeing results. I also need a fuller record of the starting weights and conversion steps. These benchmark translations have not received an independent native-speaker audit in this study. The agent-safety volunteers reviewed a different dataset."
    )
    p(
        "I have listed the other 300 parallel questions from the same 600-row benchmark. They do not overlap with this analysis, and I have not run confirmation inference on them. Before doing so, I would agree the block order and repeated subset, use a reserved host, record how both model files were produced, balance which configuration runs first and retain every failed request. Those execution details are not finalised. The questions come from the same benchmark, rather than a separate corpus."
    )
    p("Questions for review", heading)
    p(
        "Does this comparison address a useful question? Given the poor class behaviour, should I first establish a suitable model and prompt in a separate development phase before running confirmation?"
    )
    p("Data and code", heading)
    url = "https://github.com/Eunini/phone-cloud-nigerian-ai/tree/main/report/focused-study"
    p(
        f'<link href="{url}" color="#18766e">Protocol, results, source hashes and analysis code</link>.',
        small,
    )
    p(
        "From the repository root, install the dev and review extras, then run python -m bench.data, python -m bench.focused_nli, python -m bench.focused_review and pytest -q. Data preparation reads the pinned benchmark. The analysis sends no requests to a model. The original run files and earlier protocol are unchanged.",
        small,
    )
    pages = []

    def footer(canvas, doc):
        pages.append(canvas.getPageNumber())
        canvas.setFont("Review", 7)
        canvas.setFillColor(colors.HexColor("#52626e"))
        canvas.drawString(48, 30, "Inioluwa Atanda | Methodological review note | 2 November 2026")
        canvas.drawRightString(A4[0] - 48, 30, str(canvas.getPageNumber()))

    output = folder / "Inioluwa-Quantization-Review-Note-2026-11-02.pdf"
    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=48,
        rightMargin=48,
        topMargin=42,
        bottomMargin=50,
        author="Inioluwa Atanda",
        title="Q4 and Q8 accuracy in Yoruba and English",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    if max(pages) != 3:
        raise ValueError("Review note no longer fits its intended three-page structure")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, default=Path("report/focused-study"))
    parser.add_argument("--font-dir", type=Path, default=Path("/usr/share/fonts/truetype/dejavu"))
    args = parser.parse_args()
    result = json.loads((args.folder / "results.json").read_text())
    (args.folder / "results.md").write_text(markdown(result))
    output = render_pdf(result, args.folder, args.font_dir)
    print(json.dumps({"pdf": str(output), "pages": 3, "new_inference_requests": 0}))


if __name__ == "__main__":
    main()
