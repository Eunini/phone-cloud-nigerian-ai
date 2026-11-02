"""Build a concise review note from the frozen paired analysis, without inference."""

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape


def interval(value):
    lo, hi = value["ci95_pp"]
    return f"{value['estimate_pp']:+.2f} pp [{lo:+.2f}, {hi:+.2f}]"


def markdown(result):
    lines = [
        "# Paired AfriXNLI analysis: results",
        "",
        "**Inioluwa Atanda · 2 November 2026 · Exploratory; no new inference.**",
        "",
        "## One bounded finding",
        "",
        "The estimated Yoruba-minus-English difference in Q4_K_M-minus-Q8_0 "
        f"accuracy change is **{interval(result['contrasts']['interaction'])}** "
        "on 300 parallel questions. The nominal paired 95% interval spans zero. "
        "These records do not establish a greater Yoruba compression penalty, "
        "equivalence, or a causal effect of bit width.",
        "",
        "| Input language | Configuration | Correct / 300 | Accuracy | Failed attempts |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for cell in result["cells"]:
        lines.append(
            f"| {cell['language']} | {cell['quantization']} | {cell['correct']} / "
            f"{cell['n']} | {cell['accuracy_percent']:.2f}% | {cell['failed_attempts']} |"
        )
    lines += ["", "| Paired contrast | Estimate and nominal 95% interval |", "| --- | --- |"]
    for key, label in [
        ("eng", "English: Q4 minus Q8"),
        ("yor", "Yoruba: Q4 minus Q8"),
        ("interaction", "Yoruba change minus English change (primary)"),
    ]:
        lines.append(f"| {label} | {interval(result['contrasts'][key])} |")
    lines += [
        "",
        "![Paired accuracy and contrast intervals](paired-analysis.png)",
        "",
        "Equal English accuracy does not mean identical answers: four questions "
        "are correct only in Q4, and four only in Q8. For Yoruba those counts are "
        "six and one. Pairing retains this information.",
        "",
        "## Class-level failure",
        "",
        "| Language | Configuration | Entailment recall | Neutral recall | Contradiction recall |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for cell in result["cells"]:
        recall = cell["class_recall_percent"]
        lines.append(
            f"| {cell['language']} | {cell['quantization']} | "
            f"{recall['entailment']:.2f}% | {recall['neutral']:.2f}% | "
            f"{recall['contradiction']:.2f}% |"
        )
    lines += [
        "",
        "Both Yoruba configurations make zero neutral predictions. English neutral "
        "recall is also poor. Each language has 99 entailment, 102 neutral and 99 "
        "contradiction gold labels; the observed majority-label baseline is 34%. "
        "Yoruba predictions heavily favour entailment. This limits what a "
        "quantization comparison near that baseline can tell us.",
        "",
        "I have not established whether this pattern comes from model capability, "
        "the English-instruction prompt, benchmark translations or another source. "
        "I did not change the prompt or select a more forgiving parser after seeing it.",
        "",
        "## Format, tokens and request failures",
        "",
        "All 1,200 final responses are parseable under the original scorer, and none "
        "stops at the output token cap. There is one failed English Q8 request before "
        "a successful retry: 1,201 attempts, 1,200 final responses, 300 paired clusters. "
        "The failure remains in the immutable source log. Invalid-format answers and "
        "output caps therefore do not explain these four observed accuracy values.",
        "",
        "Reported prompt-token ranges are 72–124 for English and 92–281 for Yoruba "
        "in both configurations. Equal output budgets do not equalise input tokenisation. "
        "The setup uses English instructions and answer labels with translated premises "
        "and hypotheses; it is not a fully Yoruba interaction.",
        "",
        "## Interpretation limits",
        "",
        "I chose this narrower analysis after inspecting the broader results. The "
        "conditions ran sequentially on different dates on shared hardware. The paired "
        "bootstrap captures question variation, not execution drift or repeat variability. "
        "Both artifacts share a pinned official GGUF release, but their complete upstream "
        "conversion/calibration lineage is not recorded. Q4_K_M and Q8_0 are different "
        "quantization recipes; Q8_0 is not an uncompressed control. AfriXNLI translation "
        "quality has not received an independent native audit in this study.",
        "",
        "## What I changed and what remains",
        "",
        "I have narrowed the question, matched the four cells by question ID, independently "
        "rescored outputs, added paired intervals and class diagnostics, preserved failures, "
        "and excluded provider/hardware/cost comparisons from the main claim. Raw "
        "observations and the earlier wider protocol are unchanged.",
        "",
        "I reserved the disjoint 300-question complement for a possible fresh confirmation. "
        "No confirmation run has happened. Balanced condition order, a reserved host, "
        "conversion provenance, repeat checks and translation review remain design work "
        "to resolve before that experiment. The holdout is from the same benchmark.",
        "",
        "See [the revised protocol](protocol.md), [analysis plan](analysis-plan.json), "
        "[runtime evidence](provenance.json), [confirmation proposal](confirmation-plan.json) "
        "and [paired outcomes](paired-results.csv). Run `python -m bench.focused_nli` "
        "and `python -m bench.focused_review` from the repository root. No model "
        "requests are made by either command.",
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

    p("Quantization and language:<br/>a focused AfriXNLI analysis", title)
    p(
        "<b>Inioluwa Atanda · 2 November 2026</b><br/>Exploratory revision for methodological review. Not preregistered or peer reviewed.",
        small,
    )
    p("One question", heading)
    p(
        "For the released Qwen2.5-1.5B-Instruct GGUF artifacts, does the Q4_K_M-minus-Q8_0 accuracy change differ between Yoruba and English on AfriXNLI?"
    )
    p(
        "I have narrowed the earlier multi-provider benchmark to one model, one task, two languages and two released configurations. This note re-analyses existing observations; it contains no new model inference."
    )
    table(
        [
            ["Input language", "Q8_0", "Q4_K_M"],
            ["English", "300 questions", "Same 300 questions"],
            ["Yoruba", "300 parallel translations", "Same 300 translations"],
        ],
        [90, 200, 209],
    )
    p("Design and primary outcome", heading)
    p(
        "The primary contrast is the Yoruba Q4-minus-Q8 accuracy change minus the English change. Negative values mean a greater measured Yoruba loss. Each parallel question carries all four outcomes: 300 paired clusters, not 1,200 independent questions."
    )
    p(
        "Both artifacts share a pinned official GGUF release. The recorded workspace, runtime binary, CPU-only two-thread settings, 2,048-token context, English instructions/labels, greedy decoding, seed, 128-token answer budget and strict scorer are matched. For each item I also check that request sizes and reported prompt-token counts match between configurations."
    )
    p(
        "I independently reparse and rescore the responses, reject duplicate successful answers or missing cells, and preserve request failures. I resample parallel IDs jointly for 10,000 bootstrap replicates, seed 20261102, and report nominal 95% percentile intervals. These intervals are conditional on the recorded runs."
    )
    p("Boundaries", heading)
    p(
        "The scope was narrowed after results were inspected. The original conditions ran sequentially on different dates on a shared host. The full upstream conversion/calibration chain is not recorded. Q8_0 is compressed; the recipes differ as well as nominal precision. This is an exploratory comparison of released configurations, not a pure causal bit-width experiment."
    )
    p(
        "I exclude other tasks, languages, model families, GPU/API providers, translation pipelines and timing repeats. I make no serving-cost, latency, phone or production claim."
    )

    story.append(PageBreak())
    p("Measured result", title)
    value = result["contrasts"]["interaction"]
    p(
        "<b>Primary contrast: "
        + interval(value)
        + ".</b> The interval spans zero. These observations do not establish a greater Yoruba compression penalty, equivalence, or a general effect of bit width."
    )
    rows = [["Language", "Configuration", "Correct / 300", "Accuracy"]]
    for cell in result["cells"]:
        rows.append(
            [
                cell["language"],
                cell["quantization"],
                str(cell["correct"]),
                f"{cell['accuracy_percent']:.2f}%",
            ]
        )
    table(rows, [85, 135, 140, 139])
    rows = [["Paired contrast", "Estimate [nominal 95% interval]"]]
    for key, name in [
        ("eng", "English: Q4 minus Q8"),
        ("yor", "Yoruba: Q4 minus Q8"),
        ("interaction", "Yoruba change minus English change"),
    ]:
        rows.append([name, interval(result["contrasts"][key])])
    table(rows, [270, 229])
    story.append(Image(str(folder / "paired-analysis.png"), width=499, height=202))
    p(
        "The bootstrap resamples all four outcomes together. Equal English accuracy still hides answer changes: four questions are correct only in Q4 and four only in Q8. The corresponding Yoruba counts are six and one. These are question-level observations from single recorded condition runs.",
        small,
    )
    p(
        "All 1,200 final responses are parseable, and none stops at the output token cap. One English Q8 request failed before a successful retry; that attempt remains in the raw log. Formatting failure and output caps therefore do not explain the four accuracy values."
    )

    story.append(PageBreak())
    p("Diagnostics and remaining controls", title)
    p("Class bias limits interpretation", heading)
    table(
        [
            ["Language", "Configuration", "Neutral recall"],
            *[
                [
                    cell["language"],
                    cell["quantization"],
                    f"{cell['class_recall_percent']['neutral']:.2f}%",
                ]
                for cell in result["cells"]
            ],
        ],
        [110, 190, 199],
    )
    p(
        "Neither Yoruba configuration ever predicts neutral. English neutral recall is poor too. Gold counts are identical across languages: 99 entailment, 102 neutral and 99 contradiction; the observed majority-label baseline is 34%. Yoruba predictions heavily favour entailment. I have not established whether the cause is model capability, prompting, translations or another source."
    )
    p(
        "Reported prompt-token ranges are 72–124 in English and 92–281 in Yoruba. The study uses English instructions and labels with translated premises/hypotheses. I did not change the prompt or relax the parser after observing the failures."
    )
    p("What still needs a fresh design", heading)
    p(
        "A shared host and sequential collection leave execution-order and contention confounding. Question bootstrap intervals do not capture this, run-to-run variation, translation error or post-hoc selection. The official artifact revision is pinned, but the full common unquantized-weight/conversion lineage needs recording for a compression-process claim. Independent native review of these benchmark translations has not been completed; the agent-safety volunteers reviewed a different dataset."
    )
    p(
        "I have reserved the unused 300-question complement of the same 600-row benchmark. No confirmation inference has happened. The proposal is to freeze a bounded execution plan on a reserved host, document common conversion lineage, balance configuration order across question blocks, preserve all failures and preselect a repeat-agreement check. Block order and repeated-subset IDs are not frozen yet. This is a within-benchmark holdout, not an independent corpus."
    )
    p("What I would like reviewed", heading)
    p(
        "Is the language-by-configuration contrast an appropriate focused target? Given the severe class bias, should a separate development phase establish a suitable prompt/model before any confirmatory run?"
    )
    p("Evidence and reproduction", heading)
    url = "https://github.com/Eunini/phone-cloud-nigerian-ai/tree/main/report/focused-study"
    p(
        f'<link href="{url}" color="#18766e">Protocol, immutable input hashes, paired outcomes, diagnostics and analysis code</link>.',
        small,
    )
    p(
        "From the repository root: install the project with its dev and review extras; run python -m bench.data, python -m bench.focused_nli, python -m bench.focused_review and pytest -q. Data preparation retrieves the pinned benchmark; the analysis makes no model requests. The original run files and broad protocol remain unchanged.",
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
        title="Quantization and language: focused AfriXNLI review note",
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
