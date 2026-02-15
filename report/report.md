# Phone or cloud? The cost of AI in Nigerian languages

Status: complete Kaggle comparison, partial commercial measurements; physical-device comparison pending.

## Question and data

Which local or cloud option reaches a stated accuracy threshold at the lowest
marginal cost for Yoruba, Hausa, Igbo and English? Use 300 AfriMMLU, 300 AfriXNLI
and all 250 AfriMGSM test items per language. The three pinned dataset releases
yield 3,400 total items. Sampling uses the same seeded row indices across
languages; original gold-answer agreement is checked before evaluation.

## Method

Use identical English instruction templates with language-specific question
content. Record the template version. Require unambiguous canonical answers:
A–D, one of three NLI labels, or a numeric math answer. Invalid answers count as
incorrect; never extract an arbitrary number from reasoning. Temperature is zero,
with the same output budget. Shuffle evaluation order using a fixed seed.

Evaluate three small model families, each at Q4_K_M and Q8_0, a larger model on
a Kaggle vLLM endpoint and a versioned commercial free-tier endpoint. Record model
hash, llama.cpp commit, physical device, OS, memory, threads and thermal state.
Run a separate local-translation condition, including translation overhead.

Measure streamed first text, first complete whitespace-delimited word, full
latency, generation rate, process RSS sampled every 50 ms and application-body
bytes. Very short answers can arrive as one chunk, so first-word time can equal
completion time. OS RSS is not a high-frequency hardware memory trace.

## Results and chart

The Qwen2.5-7B-Instruct AWQ run on a Kaggle T4 completed all 3,400 unique items
with 3,400 successful responses and 1,239 correct answers under the fixed
128-token budget. Per-task results avoid pooling unlike tasks:

| Language | AfriMMLU (300) | AfriXNLI (300) | AfriMGSM (250) |
| --- | ---: | ---: | ---: |
| English | 73.00% | 88.00% | 27.60% |
| Yoruba | 37.67% | 41.33% | 3.20% |
| Hausa | 37.00% | 32.33% | 1.60% |
| Igbo | 38.67% | 37.33% | 0.80% |

All 2,400 knowledge/logic responses were parseable and ended normally. For
math, 734 of 1,000 responses ended at the token cap and only 270 were parseable.
The low math scores therefore combine reasoning, language, format-following and
budget limits. A separately declared larger-budget sensitivity run is needed
before attributing the gap to language understanding. The original results are
retained. Provenance records the model revision, vLLM 0.11.2, runtime packages,
evaluation source commit and corpus hash.

Latency is client/server loopback on the Kaggle host, not mobile WAN latency.
The free research quota does not supply a permanent public endpoint. Its
payload-cost scenario can be plotted but is excluded from the final cheapest
deployment decision table.

The first Gemini Flash Lite free-tier batch recorded 450 requests, including 395
successful responses and 55 HTTP 503 failures. Of those 450 attempted items, 237
were answered correctly. This is a shuffled partial sample, not the final
language/task comparison. Results retain all request failures and retries.
The fixed 48-question shared-Linux pilot is an integration check; no physical
phone measurements are available yet.

`bench.report` generates
`report/results/summary.csv`, `accuracy-cost.png` and `decisions.json` from measured
run files. The predeclared example accuracy threshold is 60%; revise it only with
an explicit reason before inspecting final comparisons. If no option reaches it,
the decision table reports no eligible option.

## Cost

![Accuracy and payload-cost scenarios](results/accuracy-cost.png)

Use decimal MB and unrestricted bundle volumes. Checked 2026-10-25: MTN's
NGN 2,000 / 2.7 GB bundle, Airtel's NGN 2,000 / 3 GB bundle, and MTN PAYG at
NGN 3.07/MB. These imply about NGN 0.741/MB, 0.667/MB and 3.07/MB, respectively.
Official pages and exclusions are recorded in `configs/tariffs.json`.

For a cloud option, `1000 × MB/question × NGN/MB` is added to observed token
billing or measured self-hosted inference cost. A USD price requires a separately
sourced, dated exchange rate. Free-tier scenarios must be labelled and quota
limited. The current byte measure excludes transport overhead and therefore is
not exact billed data consumption. Initial model downloads, power, hardware,
idle server time, unsuccessful calls and bundle expiry need separate accounting.

## Translation, error analysis and limitations

Review a language-balanced sample of translation and answer-extraction failures.
Report math, knowledge and NLI separately. English prompting, training-data
contamination, correlated parallel items, thermal throttling and mobile network
variability limit interpretation. Do not generalize a workstation result to a
phone or a free API allowance to sustained commercial serving.

## Conclusion

The datasets, reproducible evaluator and cost model are ready. Complete device/cloud runs,
repeated performance measurements and translation review are needed before an
accuracy/cost trade-off or final CV percentage can be reported.
