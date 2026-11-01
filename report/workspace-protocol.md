# Workspace CPU-server protocol

I revised the scope on 2026-10-26, before collecting the full CPU matrix, to
run the experiments in the workspace. I retained the repository name for
continuity. Phone/laptop measurements are outside this study, and I draw no
physical-device conclusion.

Run Qwen2.5-1.5B-Instruct and SmolLM2-1.7B-Instruct, each at Q4_K_M and Q8_0.
These two Apache-2.0 families and their GGUF repository revisions were already
listed in `configs/models.json`; selection does not depend on CPU accuracy.
Download one condition at a time and verify its published LFS SHA256 and size.
Record actual weights, source revision, binary hash, hardware, OS and load.

Use the pinned llama.cpp revision `6050b467c07a95c7b87debd4ddac2f8ba8d9b807`,
two inference and batch threads, zero GPU layers, context 2048, one request at
a time, seed 2026 and the evaluator's existing temperature-zero/128-token prompt.
Measure full accuracy on the unchanged 3,400 items. Completed incorrect answers
are never resampled; request errors have at most three attempts and remain in
accuracy and payload accounting. Run three repetitions of the existing
preselected 120-item stratified timing set. Timing subsets do not enter final
accuracy decisions. Warmups stay separate.

Use Qwen Q4 as the predeclared translation intervention, independently of its
baseline accuracy. It translates the actual question to English through the
same CPU endpoint, answers, and translates answer presentation back. Record the
entire pipeline and sampled client/server RSS. Never substitute the parallel
English gold question. Full translated accuracy and three timing repeats are
separate conditions. Translation quality remains an open limitation requiring
human review; automatic JSON conformance is not a translation-quality score.

The controller is finite (24-hour default, 48-hour maximum), single-instance
locked, resumable only with matching source/data/binary provenance and bounded
per-process timeouts. The local service initially used a two-core quota and an
8-GiB memory cap; the dated memory-limit repair below records the later change.
It stops its own model server after each condition and on handled termination.
It starts no AWS, Kaggle or paid API resources. Existing quota-limited commercial
continuation is separate. Run with:

```bash
python -m bench.workspace --server /absolute/pinned/build/bin/llama-server \
  --scratch /external/temporary/model-cache --threads 2 --max-hours 24
```

This workspace is virtualized and shared with unrelated services. A two-core
quota does not reserve physical cores. Record load and treat measured latency as
this host's operating point. A 24-hour timeout is partial evidence, never a
completed benchmark. Native review and human judge calibration elsewhere in the
portfolio remain pending.

`bench.continue_workspace` supervises the pinned study for at most seven days
and 32 timeout resumptions. Its persisted absolute expiry does not reset when
restarting the supervisor. Only recorded controller/child timeouts with a new
timestamp and unchanged worker command can resume. Storage failures, model
errors and operator termination require diagnosis. Systemd transport errors are
retried; a monitoring failure never kills the independently bounded worker.
Each worker retains its 24-hour bound and two-core quota. The initial 8-GiB
limit and later 12-GiB recovery limit are disclosed separately. Immutable
complete-line snapshots permit reporting without editing live JSONL; any
unflushed tail is excluded and recorded.

After the first condition completed all 3,400 items and three 120-item timing
repeats, the controller stopped at the next model's port check. TCP TIME_WAIT
was mistaken for a live listening service. The corrected port guard uses
SO_REUSEADDR and still rejects an actual listener. A regression check exercises
both cases. For the already-started study, `scripts/resume_pinned_workspace.py`
retains the original c75b734 evaluator checkout, verifies its request/scoring
source bytes against Git, and records the wrapper's hash. Only controller-side
port checks change; evaluator/model-server children and existing predictions
remain unchanged. The persisted supervision deadline is retained across this
explicit repair.

On November 1, after diagnosing the SmolLM out-of-memory failure, I raised the
service memory cap to 12 GiB, with an 11-GiB soft threshold and no worker swap.
The pinned server's default prompt-cache budget alone is 8,192 MiB, before model,
KV-cache and runtime allocations. I kept the evaluator, model-server arguments,
weights, prompts, seed and successful answers unchanged. The completed Qwen timing
runs precede this change; subsequent SmolLM runs use the revised cap. The original
supervisor expiry is retained. The [reporting context](runs/snapshots/20261101-qwen-q8/context.json)
records the interruption and recovery; the change does not turn a shared host
into a reserved-hardware benchmark.

The CPU endpoint is classified `cloud` in the cost evaluator because it is a
hosted server. Its hosting rate is unknown, so total hosting cost and naira cost
remain unknown. Report measured service seconds per question and, if useful,
the formula `USD/1000 = 1000 × seconds/question × hourly_server_price / 3600`.
A later price scenario must identify its source, date and hardware match; idle
capacity, parallelism and amortization assumptions must be explicit. Never use
an unrelated AWS instance's price as this workspace's measured price.

Nigerian mobile tariff calculations remain hypothetical remote-user payload
scenarios, based on the existing dated sources. Loopback request timing does not
measure a mobile network. Model download, network headers/TLS, power and hardware
costs remain separate. Unknown-price CPU options cannot win a cheapest-option
table through an assumed zero price.
