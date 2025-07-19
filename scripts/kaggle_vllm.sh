#!/usr/bin/env bash
set -euo pipefail
# Run in a GPU-enabled Kaggle notebook terminal with Internet enabled.
# A Kaggle free GPU allocation is not a publicly priced production cloud server.
model=${1:-Qwen/Qwen2.5-7B-Instruct-AWQ}
revision=${2:?Pass the reviewed Hugging Face weights revision}
# Use a fresh environment: vLLM is compiled against a specific PyTorch build.
python -m pip install 'vllm==0.11.2'
vllm serve "$model" --revision "$revision" --host 127.0.0.1 --port 8000 \
  --served-model-name cloud-qwen7b-awq --max-model-len 2048 --max-num-seqs 1 \
  --dtype half --quantization awq --enforce-eager --seed 2026 \
  --gpu-memory-utilization 0.80 --disable-log-requests
