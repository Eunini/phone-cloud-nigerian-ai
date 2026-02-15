# Phone or cloud? The cost of AI in Nigerian languages

**Current result:** all 3,400 evaluation items have been prepared and checked for
parallel gold-answer agreement. The Kaggle 7B model completed all 3,400 items.
The first free-tier commercial batch recorded
450 attempts: 395 successful responses and 55 HTTP 503 errors. It remains a
partial study; physical-device and full cloud comparisons are pending.

| Task | Dataset | Items per language | Original test size |
| --- | --- | ---: | ---: |
| Knowledge | `masakhane/afrimmlu` | 300 | 500 |
| Sentence logic | `masakhane/afrixnli` | 300 | 600 |
| Mathematics | `masakhane/afrimgsm` | 250 | 250 |

Languages: Yoruba (`yor`), Hausa (`hau`), Igbo (`ibo`) and English (`eng`). The math
set has 250 unique test items; it is never padded to 300 by repetition. Revisions
and selection hashes are recorded in `report/data-audit.json`.

The completed Qwen2.5-7B AWQ research run used a Kaggle T4 and the fixed
128-token output budget:

| Language | AfriMMLU (300) | AfriXNLI (300) | AfriMGSM (250) |
| --- | ---: | ---: | ---: |
| English | 73.00% | 88.00% | 27.60% |
| Yoruba | 37.67% | 41.33% | 3.20% |
| Hausa | 37.00% | 32.33% | 1.60% |
| Igbo | 38.67% | 37.33% | 0.80% |

Math is strongly limited by this budget: 734 of 1,000 math outputs reached the
token cap, and only 270 yielded a parseable canonical answer. These scores
measure answers delivered within the fixed budget; they do not isolate language
ability. Client/server timing is loopback on Kaggle, excluding phone-network
latency. Free research GPU quota is excluded from final deployment recommendations.

![Measured accuracy and payload-cost scenarios](report/results/accuracy-cost.png)

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
python -m bench.data
python -m bench.models --model qwen --quant Q4_K_M
# Build a reviewed llama.cpp checkout using scripts/build_llama.sh.
/path/to/llama-server -m models/qwen2.5-1.5b-instruct-q4_k_m.gguf \
  --alias local --host 127.0.0.1 --port 8080 --ctx-size 2048 --threads 4
```

Run in a second terminal, replacing the revision and PID with observed values:

```bash
python -m bench.run --endpoint http://127.0.0.1:8080/v1 --model local \
  --model-revision WEIGHTS_SHA256 --placement local --device 'actual device and RAM' \
  --server-pid SERVER_PID --out report/runs/qwen-q4.jsonl
```

Repeat for the three revision-pinned model candidates in `configs/models.json`,
at `Q4_K_M` and `Q8_0`. Download one model condition at a time if storage is limited.
A Linux workstation run must be described as such; it is not an Android-phone run.

For Android, create the lightweight bundle with `scripts/android_bundle.py` and
follow [the physical-device guide](report/android-guide.md). It avoids PyArrow
and PyTorch installation on Termux, and builds the pinned llama.cpp revision.
Record phone model, chipset, RAM, OS, battery/charging state, thread count and
thermal conditions. Run full accuracy once per model condition and at least
three timing repeats on the fixed 120-item sample before performance claims.

For Kaggle, see `scripts/kaggle_vllm.sh`; run the evaluator on the notebook host
against `http://127.0.0.1:8000/v1`. For a commercial free tier, export its key as
`BENCH_API_KEY`, use the provider's compatible API root and a versioned model ID,
and record quota eligibility. This repository does not assume any paid credit.

The configured commercial continuation is finite and resumes the same selection
over successive free-quota days. It makes at most 450 question attempts per day,
stops after completion or 30 quota days, and never enables billing. See
[the commercial protocol](report/commercial-run.md). Request failures are retained;
incorrect completed answers are never retried to improve accuracy.

```bash
pip install -e '.[translation]'
# Translation runs locally and is timed, including answer presentation back-translation.
python -m bench.run --endpoint http://127.0.0.1:8080/v1 --model local \
  --model-revision WEIGHTS_SHA256 --placement local --device 'actual device' \
  --server-pid SERVER_PID --translate --out report/runs/qwen-q4-translated.jsonl
python -m bench.report report/runs/*.jsonl --billing configs/billing.local.json
```

Canonical letters, NLI labels and numbers are scored before translating answer
presentation back. Translation memory/latency and possible label distortions must
be reported separately from the endpoint's own latency.

Byte measurements are exact for the serialized request body and received SSE
body. They exclude headers, TLS, TCP/IP overhead and retransmission, so mobile
data cost is an application-payload estimate, not an operator billing measurement.

Tariffs were checked **2026-10-25** using [MTN's plan page](https://www.mtn.ng/data/data-plans/),
[MTN's PAYG FAQ](https://www.mtn.ng/helppersonal/data-bundles/) and
[Airtel's plan page](https://www.airtel.com.ng/ng/personal/data/data_offers/data_plans).
The calculation uses unrestricted base data and excludes night/social bonuses.

Local inference has zero **marginal API/mobile-data** cost after downloading the
model. Hardware, electricity and download cost are not zero. Free tiers have
quotas and are not equivalent to zero production cost. Missing API prices or
currency conversion evidence produce unknown costs rather than a zero estimate.

See [background](report/background.md), [study report](report/report.md) and
[remaining work](report/completion.md). A final CV claim requires measured runs.

The local pilot completed 46 of 48 requests and recorded two pre-response
`RemoteProtocolError` failures with their request-byte costs. This is an
integration check, not an Android or final accuracy result. Pilot runs are
excluded from the cheapest-eligible decision table.
