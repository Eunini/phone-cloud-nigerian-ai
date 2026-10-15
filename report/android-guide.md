# Physical Android measurements

This procedure needs the actual phone. A Linux-host pilot cannot supply its results.
Use current Termux from its official distribution, with files in Termux's private
home rather than shared Android storage. Keep the phone offline during local runs.

On the development host, first prepare `python -m bench.data`, then create the
bundle with `python scripts/android_bundle.py --out /outside/repo/afri-phone.tar.gz`.
Copy it and one revision-pinned GGUF from `configs/models.json` to the phone by USB.
Save that GGUF's SHA256 and provenance alongside the returned results. The transfer
and one-time model download are separate costs from per-question inference.

For the prepared Android smoke release, download `afri-phone-android-v1.tar.gz`
and the pinned Qwen Q4 GGUF into Android's Downloads folder. Grant Termux shared
storage access with `termux-setup-storage`, then extract the bundle into its
private home. The setup uses Termux's packaged pip to install into a venv created
without ensurepip; Python and psutil are supplied by Termux packages.

In Termux:

```bash
tar -xzf afri-phone.tar.gz
cd afri-phone
bash scripts/termux.sh
mkdir -p models report/runs
# Put the transferred GGUF into models/model.gguf.
sha256sum models/model.gguf
.venv/bin/python -m bench.phone_smoke
# This records non-identifying hardware metadata, runs 12 actual questions,
# saves results/server logs under report/runs/, and stops its own model server.
# After the smoke result has been checked, start the server for the full run:
.llama-cpp/build/bin/llama-server -m models/model.gguf --alias local \
  --host 127.0.0.1 --port 8080 --ctx-size 2048 --threads 4 --parallel 1 \
  > report/server.log 2>&1 &
server_pid=$!
```

Wait for `curl --fail http://127.0.0.1:8080/health`. Write down the phone's model,
chipset, installed/available RAM, Android and Termux versions, battery/charging
state, room temperature, thread count and any thermal warning. Keep conditions
consistent, allow the phone to cool between runs, and do not run competing apps.
Replace the quoted metadata and hash below with observed values. An optional
`--limit 12` smoke run must use a separate output path and is never a full result.

```bash
.venv/bin/python -m bench.run --endpoint http://127.0.0.1:8080/v1 --model local \
  --label qwen-1.5b-Q4_K_M --model-revision ACTUAL_GGUF_SHA256 \
  --placement local --device 'ACTUAL phone/chipset/RAM/OS/conditions' \
  --server-pid "$server_pid" --out report/runs/qwen-q4-full.jsonl
```

Run all 3,400 questions once per model/quantization for accuracy. For repeated
timing, choose the same 120-item stratified subset before examining outputs:

```bash
.venv/bin/python -m bench.timing
for repeat in 1 2 3; do
  .venv/bin/python -m bench.run --items data/prepared/timing120.jsonl --limit 120 \
    --endpoint http://127.0.0.1:8080/v1 --model local --label qwen-1.5b-Q4_K_M \
    --model-revision ACTUAL_GGUF_SHA256 --placement local \
    --device 'ACTUAL phone/chipset/RAM/OS/conditions' --server-pid "$server_pid" \
    --replicate "$repeat" --out "report/runs/qwen-q4-timing-$repeat.jsonl"
done
kill "$server_pid"
```

Keep the server running until the repetitions finish, then stop it. Keep identical
thermal conditions and allow cooling between repetitions. `--limit 120` marks
these timing samples partial, excluding them from final accuracy decisions.
Interrupted runs resume successful question IDs in the same file; errors remain
in the byte-cost accounting. Repeat with three candidate models at Q4_K_M and
Q8_0, one file at a time if necessary.
Return the JSONL files, warmup files, server logs, provenance and device notes by
USB. The evaluator records 50 ms sampled server RSS when Android permits access;
an unavailable value must be reported as missing, never zero.

The bundle installs only HTTP and process measurement dependencies. Dataset
preparation, plotting, PyArrow and PyTorch are not required on Android. For the
phone translation experiment, the same local GGUF server can translate using:

```bash
# Add these flags to a separate full accuracy run and separate timing files:
--translate --translation-endpoint http://127.0.0.1:8080/v1 \
--translation-model local --translation-revision ACTUAL_TRANSLATOR_GGUF_SHA256
```

This performs real translation requests on the phone; it never substitutes the
parallel English reference question. Translation quality is not assumed and
needs native review. Invalid translation JSON is an error, not a successful
answer. Record the translator's weights and full translation/answer/back-translation
time. RSS sampling covers translation, answer generation and presentation. Client and
server PID peaks are separate measurements, excluding external process trees and
GPU allocations; their sum is not a measured simultaneous total-memory peak. The alternative
pinned NLLB translator requires the separate laptop/PyTorch environment and must
be described as such. Reusing the answering model as translator tests a different
intervention from adding a dedicated NLLB model; report them separately.
