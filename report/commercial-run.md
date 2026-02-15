# Commercial free-tier run

Use the verified `gemini-3.1-flash-lite-preview` model through Google's OpenAI
compatible API root `https://generativelanguage.googleapis.com/v1beta/openai`.
The 2026-10-26 discovery response reports version `3.1-flash-lite-preview-03-2026`.
The account owner verified Free tier with billing unlinked in AI Studio and
reported limits of 15 requests/minute, 250,000 tokens/minute and 500 requests/day.
The quota is shared with other calls to this model family. Preview weights may
change even when the API model ID stays fixed; timestamps are mandatory.

The operator loads the dedicated key from its private external credential file
into the evaluator environment. Never include it in a shell command, notebook,
result, source file or URL. Use a five-second minimum request interval and at
most 450 new questions per batch, reserving room for warmup and diagnostics:

```bash
python -m bench.run \
  --endpoint https://generativelanguage.googleapis.com/v1beta/openai \
  --model gemini-3.1-flash-lite-preview --label gemini-3.1-flash-lite-preview-free \
  --model-revision 3.1-flash-lite-preview-03-2026 \
  --placement cloud --device 'Google Gemini Developer API; provider hardware undisclosed' \
  --min-interval 5 --max-new-requests 450 \
  --out report/runs/gemini-flash-lite-full.jsonl
```

Resume the same command/file only after the daily quota resets. Google documents
the daily reset at midnight Pacific time; a model-family quota may stop the run
earlier. Authentication/permission/rate-limit responses stop the evaluator and
preserve progress. It never enables billing or changes provider safety settings.
Until every task/language group is complete, the report marks it partial and
excludes it from the final decision table. Completing 3,400 questions at 500/day
needs at least seven quota days, before translation and safety-study calls.

The first batch recorded 450 question attempts: 395 successful responses and
55 HTTP 503 failures. Continue with `python -m bench.resume_commercial` on the same
host and private credential profile. It reserves a process lock, waits until
00:05 Pacific after a quota-day boundary, and caps each day at 450 question
attempts. Each item has at most three request attempts; a completed answer,
including an incorrect answer, is never sampled again. The run ends once all
3,400 items succeed or reach that failure limit, or after 30 quota days. It
requires the saved profile to confirm free tier and billing unlinked before
every batch. Other experiments share the remaining daily allowance.

In this workspace the finite continuation runs as the dedicated local service
`afri-research-commercial.service`, under the workspace user. It survives the
chat's terminal sessions, has a 30-day runtime limit, and reads credentials only
from the user's private configuration. It does not start AWS or GPU resources.
The external private log and progress file show whether it is waiting, active
or finished. A stopped service must be inspected before restarting; there is no
automatic restart loop for authentication errors.

Generate the chart with `--billing configs/billing.free-tier.json`. API cost is
zero only while the free-tier quota applies; mobile application-body costs still
use the dated MTN/Airtel tariffs. The 1,000-question figure is an extrapolation,
not a claim that 1,000 free requests can be made in one day.

Sources: [compatibility](https://ai.google.dev/gemini-api/docs/openai),
[pricing](https://ai.google.dev/gemini-api/docs/pricing),
[quota definitions](https://ai.google.dev/gemini-api/docs/rate-limits).
