# Can extra answer space and free-form responses help?

Exploratory follow-up, November 5, 2026. This is the IrokoBench maths study,
separate from the agent-safety project's harmless technical diagnostic.

I want to separate two possible explanations for low strict scores: a response
may have been cut off, or its answer may not have used the requested format.
Neither issue establishes that the underlying reasoning was correct.

The fixed pilot contains 50 AfriMGSM questions: 12 parallel source problems in
English, Yoruba, Hausa and Igbo, plus one additional English/Yoruba pair. That
gives 13 English, 13 Yoruba, 12 Hausa and 12 Igbo questions. Item selection uses
seed 20261105 and does not inspect previous answer correctness. These questions
come from an already evaluated test set, so this is not independent confirmation.
The [plan](plan.json) records the exact IDs, weights, binary and source hashes.

Every question receives four conditions with the same Qwen2.5-1.5B Q4 model:
original prompt/128 tokens; original prompt/1,024; free-form prompt/128;
free-form prompt/1,024. Request order is shuffled with the recorded seed. All
four conditions use context 4,096, two CPU inference threads, zero GPU layers,
temperature zero and seed 2026. The historical benchmark used context 2,048;
the new experiment therefore includes a fresh original-prompt/128-token control
rather than attributing a historical-score difference solely to output length.

Free-form prompting removes the `FINAL:` instruction and allows an explanation.
The larger budget is finite, not unlimited. Cutoffs remain visible. The runner
stops within two hours plus at most one in-flight request, and shuts down its
own loopback model server. No paid APIs, new AWS instances or GPU jobs are used.
Existing workspace hosting is not claimed to have zero operating cost.

## Scoring without quietly improving the original numbers

The unchanged strict extractor is applied to every response. A second,
pre-specified diagnostic looks for exactly one numeric literal on the last
nonempty line, allowing surrounding words or units. It does not scan for the
gold answer or pick whichever number matches it. Multiple-number statements,
equations and fractions remain unparseable and need independent review.
The parser does not constitute a complete semantic assessment.

Report strict and relaxed correctness, unparseable responses, cutoffs and API
failures separately. Also report relaxed correctness restricted to uncapped
responses: a cutoff can leave an intermediate number that happens to match
the expected answer. Do not interpret such a match as a complete solution.
Wrong numeric answers remain wrong, regardless of formatting. Ambiguous output
is not evidence that the model failed to understand the language.

The existing 3,400-item benchmark files and main scores are left unchanged.
Private response journals go under `runs/private/maths-ablation-v1/`; public
results contain counts. A full rerun or a new primary scoring policy should
follow inspection and independent adjudication of this pilot, not an assumption
that removing constraints must improve performance.

```bash
../../.venv/bin/python -m bench.maths_ablation \
  --server ../../tools/llama-workspace/build/bin/llama-server
```

The runner writes `results.json` progressively and records server shutdown.
Only a report marked complete with 50 successful responses per condition is a
completed pilot. No results are claimed in this plan before collection.
