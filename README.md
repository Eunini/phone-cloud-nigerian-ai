# Quantization and language: a paired AfriXNLI analysis

I compare Q4_K_M and Q8_0 versions of Qwen2.5-1.5B-Instruct on matched English and Yoruba AfriXNLI questions.

I narrowed this study on **2 November 2026** after inspecting the broader benchmark results. This is an exploratory analysis for methodological review, not a preregistered experiment or a completed paper.

## Question

Does the change in AfriXNLI accuracy from Q8_0 to Q4_K_M differ between Yoruba and English for Qwen2.5-1.5B-Instruct?

## Results

I compared the Q4-minus-Q8 accuracy change in each language using **300 matched question pairs**. The difference between the two changes is **+1.67 percentage points**, with a paired 95% bootstrap interval of **-0.67 to +4.33**. The interval includes zero, so I cannot conclude that Yoruba had a greater compression penalty. This also does not show that the configurations are equivalent.

| Input language | Q8_0 | Q4_K_M |
| --- | ---: | ---: |
| English | 195 / 300 (65.00%) | 195 / 300 (65.00%) |
| Yoruba | 104 / 300 (34.67%) | 109 / 300 (36.33%) |

![Accuracy and paired contrasts](report/focused-study/paired-analysis.png)

**A substantial task limitation:** neither Yoruba configuration predicts the neutral class at all. English neutral recall is poor too. The observed majority-label baseline is 34%. All 1,200 final responses are parseable and none hits the output cap, so those two mechanisms do not explain these accuracy values. One failed request is retained before its successful retry.

## What I controlled, and what I did not

The existing records match the selected parallel questions, original scorer, English instructions/answer labels, output budget, pinned runtime binary and recorded two-thread CPU setup. The analysis independently rescores every response, verifies hashes, retains failures and resamples all four outcomes together by question ID.

The configurations ran on different dates on a shared server. Q4_K_M and Q8_0 use different recipes, and Q8_0 is compressed too. I do not have the full record of the starting weights, conversion and calibration. The translations have not received an independent native-speaker audit in this study. These limits prevent conclusions about bit width alone, general language understanding, latency or cost.

## Review materials

- [Revised protocol and scope boundaries](report/focused-study/protocol.md)
- [Three-page review note (PDF)](report/focused-study/Inioluwa-Quantization-Review-Note-2026-11-02.pdf)
- [Results, uncertainty and class-level diagnostics](report/focused-study/results.md)
- [Machine-readable results](report/focused-study/results.json) and [300 paired outcomes](report/focused-study/paired-results.csv)
- [Analysis specification](report/focused-study/analysis-plan.json) and [hashed runtime evidence](report/focused-study/provenance.json)
- [Proposed confirmation using the unused 300-question complement](report/focused-study/confirmation-plan.json). No confirmation predictions collected.

## Reproduce

Use Python 3.12 from the repository root:

```bash
pip install -e '.[dev,review]'
python -m bench.data
python -m bench.focused_nli
python -m bench.focused_review
pytest -q
```

Data preparation reads revision-pinned public IrokoBench datasets and must reproduce the original audited selection hash. The two analysis commands make no model requests. They check the saved Q4 and Q8 run files against their recorded hashes, regenerate the metrics, paired CSV and figure, and build the review note. The PDF renderer uses DejaVu Sans fonts; its font directory is configurable.

## Earlier exploratory benchmark

The earlier CPU, GPU and API comparisons, mobile-data cost estimates, other tasks and translation experiment are documented in the [archived broader overview](report/broad-benchmark-overview.md), [dated report](report/report.md), [original CPU protocol](report/workspace-protocol.md) and [completion tracker](report/completion.md). Those extra runs do not enter this paired analysis. Phone/laptop measurement remains outside the workspace study. The raw observations, original protocol and historical counts are preserved.
