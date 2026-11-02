# Revised study: quantization configuration and language on AfriXNLI

**Inioluwa Atanda · 2 November 2026 · Exploratory analysis, prepared after inspecting the broader results.**

## One question

For the released Qwen2.5-1.5B-Instruct GGUF artifacts on this CPU setup, does the Q4_K_M-minus-Q8_0 accuracy change differ between Yoruba and English on AfriXNLI?

I have narrowed the research question to one model, one task, two languages and two released quantization configurations. The earlier multi-provider benchmark remains a separate exploratory inventory. I am not using it to attribute an effect to language or compression.

## Four conditions and one primary contrast

| Input language | Q8_0 | Q4_K_M |
| --- | --- | --- |
| English | 300 selected AfriXNLI questions | The same 300 questions |
| Yoruba | Their 300 parallel translations | The same 300 translations |

The primary contrast is the Yoruba Q4-minus-Q8 accuracy change minus the English Q4-minus-Q8 change. A negative value means a greater measured Yoruba loss. The question allows either direction or an uncertain result; I am not assuming compression must harm Yoruba more.

The unit is the **parallel question ID**, giving 300 four-outcome clusters, not 1,200 independent questions. Dataset revision, row indices, gold labels, run files and model artifacts are pinned in [the analysis plan](analysis-plan.json). I require matching gold labels across parallel items. This checks label alignment, not translation quality.

## What the existing records hold fixed

- Qwen2.5-1.5B-Instruct model family and parameter count. Both released artifacts come from the same pinned official GGUF repository revision.
- Recorded workspace, llama.cpp revision and server binary; CPU-only inference, two inference/batch threads, one slot and a 2,048-token context.
- Original selected question IDs, English instruction template and English answer labels. Only the premise and hypothesis change language.
- Greedy decoding, recorded server seed 2026, 128-token output budget and original strict scorer. Matching serialized request sizes and reported prompt-token counts are checked between configurations for each item.

Q4_K_M and Q8_0 change the quantization recipe as well as nominal precision. Q8_0 is compressed too. I therefore compare these **released configurations**, not a pure bit-width intervention or an uncompressed baseline. The full upstream unquantized-weight/conversion/calibration chain was not recorded. Shared-host contention and collection date/order were not controlled. The existing records support a paired exploratory comparison, not a fully randomised causal experiment.

The copied, hashed runtime receipts are in [provenance.json](provenance.json). Reusing identical setup metadata does not establish identical physical CPU availability at every request.

## Scoring and uncertainty

I independently reparse and rescore every selected response against the original gold answer. Stored predictions and correctness must agree. Successful wrong answers are never replaced. I reject missing question cells, repeated successful answers, mixed run identities, changed input hashes and unfinished retry sequences. The original retry ceiling is three attempts; terminal request failures count as wrong, while every failed attempt remains recorded.

The primary outcome is strict task accuracy. I separately report unparseable successful responses, output-cap stops, failed attempts, label frequencies, confusion matrices and class recall. Conditional accuracy among parseable responses is diagnostic only; it does not replace the fixed denominator.

I use 10,000 bootstrap samples, seed 20261102, resampling parallel IDs with all four outcomes together. Intervals are nominal 95% percentile intervals. They describe question-sampling variation conditional on these recorded runs. They do not account for post-hoc scope selection, translation errors, run-to-run variation, shared-host drift or model families. An interval containing zero establishes neither no effect nor equivalence. I specify no equivalence margin or formal equivalence test.

## Scope boundaries

I exclude Hausa, Igbo, other tasks/models, GPU/API endpoints, translation pipelines, timing repeats and warmups from this analysis. I make no latency, serving-cost, phone, production-reliability or general Yoruba-understanding claim. The larger matrix can provide context without supplying extra independent observations here.

The agent-safety volunteers reviewed a different prompt set. Their work is not evidence that these AfriXNLI translations are accurate. Pretraining exposure to benchmark material is also not established by this audit.

## Fresh confirmation proposed for review

I have recorded the unused complement of the original 600-row AfriXNLI test set: **300 additional parallel question IDs**, disjoint from this analysis, in [confirmation-plan.json](confirmation-plan.json). No confirmation predictions have been collected for this revision. This is a within-benchmark holdout, not an independent corpus.

Before fresh inference, I would freeze a bounded execution plan with a reserved host, documented common conversion lineage, balanced configuration order across question blocks, identical settings, complete failures, and a predetermined repeat-agreement check. The block order and repeat subset are not yet frozen; this is a proposal for review, not a registered or completed confirmatory experiment. A causal claim about bit width alone would require a separate matched-algorithm design.

I would value review of two decisions: whether the language-by-configuration contrast is the right target, and whether the severe class bias makes this model/prompt unsuitable for a confirmatory study without a separate development phase.

## Reproduce

From the repository root, rebuild the original audited selection and verify its hash:

```bash
pip install -e '.[dev,review]'
python -m bench.data
python -m bench.focused_nli
python -m bench.focused_review
pytest -q
```

The analysis checks all supplied hashes and generates no model requests. Data preparation reads the pinned public benchmark; the analysis itself is offline. Results are in [results.md](results.md), with [machine-readable metrics](results.json), [paired outcomes](paired-results.csv), and the [review PDF](Inioluwa-Quantization-Review-Note-2026-11-02.pdf).
