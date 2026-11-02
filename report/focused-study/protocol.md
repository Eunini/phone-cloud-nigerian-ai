# Comparing Q4 and Q8 on Yoruba and English AfriXNLI

Inioluwa Atanda

2 November 2026

I chose this narrower question after examining the broader benchmark results. The analysis is exploratory and was not preregistered.

## Research question

Does the change in AfriXNLI accuracy from Q8_0 to Q4_K_M differ between Yoruba and English for Qwen2.5-1.5B-Instruct?

I compare two published GGUF versions of the same model. The earlier benchmark also covered other models, tasks and providers. Those results remain available, but they are outside this comparison.

## Questions and configurations

| Input language | Q8_0 | Q4_K_M |
| --- | --- | --- |
| English | 300 selected AfriXNLI questions | The same 300 questions |
| Yoruba | Their 300 parallel translations | The same 300 translations |

For each language, I subtract Q8 accuracy from Q4 accuracy. I then subtract the English change from the Yoruba change. A negative result would mean that the change was worse for Yoruba.

Each question has four related outcomes: one for each language and configuration. I keep those four outcomes together throughout the analysis. There are 300 question pairs, rather than 1,200 independent questions.

The [analysis plan](analysis-plan.json) records the dataset version, question IDs, reference labels, run files and model files. The reference labels must agree between the English and Yoruba versions. Matching labels alone do not verify the translations.

## Settings checked in the existing runs

- Both model files come from the same version of the official Qwen GGUF repository and have the same model family and parameter count.
- The records specify the same workspace, llama.cpp version and server binary. They use CPU inference, two inference threads, two batch threads, one request slot and a context size of 2,048 tokens.
- Both configurations receive the same selected questions, English instructions and English answer labels. The premise and hypothesis are in the assigned language.
- The runs use greedy decoding, server seed 2026, a 128-token output limit and the original answer scorer. For each item, I check that the recorded request sizes and prompt-token counts agree between configurations.

Q4_K_M and Q8_0 use different quantization recipes as well as different nominal precision. Q8_0 is also compressed. The available records therefore compare two released configurations. They do not isolate the effect of bit width or provide an uncompressed baseline.

I do not have the full record of the original weights, conversion steps and calibration used to produce the two files. The runs also took place on different dates on a shared server. Their order was not randomised, and other activity on the host was not controlled.

The [runtime records](provenance.json) include hashes of the original logs and settings. Repeated setup metadata does not prove that the same amount of physical CPU capacity was available for every request.

## Scoring

I parse each selected response again and compare it with the original reference answer. The recalculated prediction and correctness must agree with the stored values.

A successful wrong answer is kept. I reject missing question outcomes, repeated successful responses, mixed run IDs, changed input hashes and unfinished retry sequences. The original limit is three attempts per item. An item that still fails after those attempts counts as wrong, and all failed attempts remain recorded.

The main score is accuracy across all selected items. I also report responses the parser cannot read, output-limit stops, request failures, prediction frequencies, confusion matrices and recall for each class. Accuracy calculated only on readable answers is a separate diagnostic and does not replace the main denominator.

## Uncertainty

I draw 10,000 bootstrap samples using seed 20261102. Each sample draws parallel question IDs with replacement and keeps the four outcomes for an ID together. I report 95% percentile intervals.

These intervals describe variation across questions in the recorded runs. They do not cover changes in translations, hardware availability, run-to-run behaviour or the decision to narrow the question after seeing results. The intervals are exploratory and should be interpreted with those limits in mind.

An interval that includes zero does not show that the configurations are equivalent. I have not specified an equivalence margin or carried out an equivalence test.

## Limits of the comparison

This analysis covers English and Yoruba AfriXNLI only. It excludes other tasks, languages, models, GPU and API endpoints, translation pipelines, timing repeats and warmup requests. I do not use it to make claims about latency, serving cost, phones, production reliability or general Yoruba understanding.

The AfriXNLI translations have not received an independent native-speaker audit in this study. The agent-safety volunteers reviewed a different set of prompts. This analysis also does not establish whether the model encountered benchmark material during pretraining.

## Proposed confirmation run

The original AfriXNLI test set has 600 rows. I have listed the other 300 parallel question IDs in [confirmation-plan.json](confirmation-plan.json). They do not overlap with the questions used here. I have not collected confirmation predictions for them. They are a holdout from the same benchmark, rather than a separate corpus.

Before running that experiment, I would agree the execution and scoring rules, use a reserved host, document how both model files were produced and balance which configuration runs first across question blocks. I would retain every failed request and choose a repeated subset in advance to check agreement between runs.

The block order, repeated subset and runtime budget have not been finalised. This is a proposal for review. A claim about bit width alone would need a separate design using a matched quantization algorithm.

I would like feedback on whether this comparison addresses a useful question. I would also like to discuss whether the poor class behaviour calls for a separate development phase to establish a suitable model and prompt before confirmation.

## Reproduction

From the repository root:

```bash
pip install -e '.[dev,review]'
python -m bench.data
python -m bench.focused_nli
python -m bench.focused_review
pytest -q
```

Data preparation reads the pinned public benchmark and must reproduce the original selection hash. The analysis then runs offline, checks its input hashes and makes no model requests.

The outputs are [the results note](results.md), [metrics](results.json), [paired outcomes](paired-results.csv), [figure](paired-analysis.png) and [review PDF](Inioluwa-Quantization-Review-Note-2026-11-02.pdf).
