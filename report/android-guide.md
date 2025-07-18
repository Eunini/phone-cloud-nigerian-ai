# Physical Android measurements

This procedure needs the actual phone. A Linux-host pilot cannot supply its results.
Use current Termux from its official distribution, with files in Termux's private
home rather than shared Android storage. Keep the phone offline during local runs.

On the development host, first prepare `python -m bench.data`, then create the
bundle with `python scripts/android_bundle.py --out /outside/repo/afri-phone.tar.gz`.
Copy it and one revision-pinned GGUF from `configs/models.json` to the phone by USB.
Save that GGUF's SHA256 and provenance alongside the returned results. The transfer
and one-time model download are separate costs from per-question inference.

In Termux:

```bash
tar -xzf afri-phone.tar.gz
cd afri-phone
bash scripts/termux.sh
mkdir -p models report/runs
# Put the transferred GGUF into models/model.gguf.
sha256sum models/model.gguf
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
  --server-pid "$server_pid" --out report/runs/qwen-q4-repeat1.jsonl
kill "$server_pid"
```

Repeat all 3,400 questions at least three times per model/quantization, using new
repeat filenames and identical conditions. Interrupted runs resume successful
question IDs in the same file; errors remain in the byte-cost accounting. Repeat
with three candidate models at Q4_K_M and Q8_0, one file at a time if necessary.
Return the JSONL files, warmup files, server logs, provenance and device notes by
USB. The evaluator records 50 ms sampled server RSS when Android permits access;
an unavailable value must be reported as missing, never zero.

The bundle installs only HTTP and process measurement dependencies. Dataset
preparation, plotting, PyArrow and PyTorch are not required on Android. The NLLB
translation condition currently requires the separate laptop/PyTorch environment;
it must not be described as translation performed on this phone. Phone translation
needs an actual locally running supported translator and separate measured overhead.
