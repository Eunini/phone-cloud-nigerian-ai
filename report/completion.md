# Completion record

Completed: exact dataset names/revisions, 3,400-item preparation, gold-label
parallelism check, strict answer extraction, streaming latency and byte logging,
memory sampling, three pinned model candidates and download tooling, dated
operator tariff evidence, cost calculation and decision/report generation.

Completed: two commercial free-tier batches, with 900 attempts covering 845
unique items. All 845 now have successful responses (480 correct), including
retries of the 55 initial HTTP 503 errors. This is partial and excluded from
final recommendations. The finite, quota-limited continuation preserves failures.

Completed: Kaggle Qwen2.5-7B AWQ evaluation on all 3,400 items. All requests
succeeded; 1,239 answers were correct at the fixed 128-token output budget.
The report explicitly records math truncation (734/1,000 outputs), loopback
latency scope and research-only GPU cost assumptions.

Pending: the complete four CPU-server model conditions, completion of the commercial comparison,
timing repeats for the remaining conditions, the local-translation condition, translation quality
review and final result tables/charts.

Update 2026-10-27 UTC: the first full CPU condition completed all 3,400 items
(744 strictly correct), with three recovered request errors. A frozen, hashed
snapshot and updated report are published. The commercial snapshot now contains
1,350 attempts / 1,295 unique items / 1,278 successful responses. Format and
output-budget failures are reported separately. The exact-choice analysis is
labelled post-hoc and leaves primary scores unchanged.

Update 2026-10-28 UTC: all three Qwen Q4 timing repeats completed, 120 successful
requests each. Their immutable snapshots and separate performance summary are
published. The Qwen Q8 full run has resumed after a documented controller-only
TCP port-check repair; all four pre-repair Q4 run files remain byte-identical.
Other CPU conditions and translation measurements remain pending.

Scope changed at the owner's request on 2026-10-26: run everything in the
workspace. Physical phone and laptop measurements are no longer required.
The primary CPU families are Qwen and SmolLM2 at two quantization levels. A
predeclared Qwen Q4 self-translation condition and three timing repeats per
condition are included. Workspace hosting price is unknown; full hosting cost
and an overall cheapest-server conclusion remain unavailable without price evidence.
