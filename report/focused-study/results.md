# Results

Inioluwa Atanda

2 November 2026

I compared Q4_K_M and Q8_0 versions of Qwen2.5-1.5B-Instruct on 300 matched English and Yoruba AfriXNLI questions. This is a reanalysis of existing answers. I chose the narrower question after examining the broader benchmark results.

## Accuracy

| Input language | Configuration | Correct / 300 | Accuracy | Failed attempts |
| --- | --- | ---: | ---: | ---: |
| English | Q8_0 | 195 / 300 | 65.00% | 1 |
| English | Q4_K_M | 195 / 300 | 65.00% | 0 |
| Yoruba | Q8_0 | 104 / 300 | 34.67% | 0 |
| Yoruba | Q4_K_M | 109 / 300 | 36.33% | 0 |

For each language, I subtracted Q8 accuracy from Q4 accuracy. I then subtracted the English change from the Yoruba change. The estimated difference is **+1.67 pp [-0.67, +4.33]**. The paired 95% bootstrap interval includes zero, so I cannot conclude that Yoruba had a greater compression penalty. This also does not show that the configurations are equivalent.

| Comparison | Estimate and 95% bootstrap interval |
| --- | --- |
| English: Q4 minus Q8 | +0.00 pp [-1.67, +2.00] |
| Yoruba: Q4 minus Q8 | +1.67 pp [+0.00, +3.33] |
| Yoruba change minus English change | +1.67 pp [-0.67, +4.33] |

![Accuracy and paired differences](paired-analysis.png)

English has 4 questions answered correctly only by Q4 and 4 only by Q8. The corresponding Yoruba counts are 6 and 1. Keeping the outcomes paired shows which questions changed, even when the overall accuracy stayed the same.

## Neutral-class errors

| Language | Configuration | Entailment recall | Neutral recall | Contradiction recall |
| --- | --- | ---: | ---: | ---: |
| English | Q8_0 | 98.99% | 0.98% | 96.97% |
| English | Q4_K_M | 94.95% | 4.90% | 96.97% |
| Yoruba | Q8_0 | 96.97% | 0.00% | 8.08% |
| Yoruba | Q4_K_M | 95.96% | 0.00% | 14.14% |

Neither Yoruba configuration predicts neutral. English neutral recall is poor too. Each language has 99 entailment, 102 neutral and 99 contradiction reference labels. Always choosing the most common label would score 34% on this sample. The Yoruba scores are close to that baseline, and most Yoruba predictions are entailment. This limits what I can learn about quantization from this model and task.

I have not established whether the cause is model capability, the English instructions, the benchmark translations or something else. I kept the original prompt and answer parser throughout this analysis.

## Answer format, token limits and failed requests

The scorer can read all 1,200 final responses, and none stops at the output token limit. One English Q8 request failed before a successful retry. That gives 1,201 attempts for 1,200 final responses, grouped into 300 question pairs. The failed attempt remains in the source log. Unreadable answers and output limits therefore do not explain these four accuracy values.

Reported prompt lengths are 72 to 124 tokens for English and 92 to 281 for Yoruba, with the same counts in both configurations. Equal output limits do not make the input token counts equal. Instructions and answer labels are in English; the premise and hypothesis are in the assigned language.

## What the results can establish

The two configurations ran one after the other on different dates on a shared host. The bootstrap describes variation across questions in those recorded runs. It does not cover changes in host activity or differences between repeated runs. I also chose this narrower question after examining the broader results.

Both model files come from the same pinned official GGUF release, but I do not have the full record of the starting weights, conversion and calibration. Q4_K_M and Q8_0 use different recipes, and Q8_0 is compressed too. The comparison cannot isolate the effect of bit width. The AfriXNLI translations have not received an independent native-speaker audit in this study.

## Before a confirmation run

I have listed the other 300 parallel questions from the same benchmark. They do not overlap with the questions analysed here. I have not run confirmation inference on them. Before doing so, I would agree the block order and repeated subset, use a reserved host, record how both model files were produced and arrange a translation review.

The original observations and broader protocol are unchanged. This revision changes the question and analysis, rather than adding a new experiment.

## Data and code

See the [protocol](protocol.md), [analysis settings](analysis-plan.json), [runtime records](provenance.json), [confirmation proposal](confirmation-plan.json) and [paired outcomes](paired-results.csv). From the repository root, run `python -m bench.focused_nli` followed by `python -m bench.focused_review`. Neither command sends requests to a model.
