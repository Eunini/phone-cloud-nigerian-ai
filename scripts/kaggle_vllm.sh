#!/usr/bin/env bash
set -euo pipefail
# Run in a GPU-enabled Kaggle notebook terminal with Internet enabled.
# A Kaggle free GPU allocation is not a publicly priced production cloud server.
model=${1:-Qwen/Qwen2.5-7B-Instruct}
revision=${2:?Pass the reviewed Hugging Face weights revision}
python -m pip install 'vllm>=0.8,<1'
vllm serve "$model" --revision "$revision" --host 127.0.0.1 --port 8000 --max-model-len 2048 --dtype half --gpu-memory-utilization 0.85
