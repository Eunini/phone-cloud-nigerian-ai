#!/usr/bin/env bash
set -euo pipefail
# Run inside Termux, with this bundle extracted in Termux private storage.
# Dataset preparation and PyArrow remain on the development host.
repo_dir=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_dir"
pkg install -y python python-psutil clang cmake git make curl
python -m venv --system-site-packages .venv
.venv/bin/python -m pip install 'httpx==0.28.1'
checkout="$repo_dir/.llama-cpp"
commit=6050b467c07a95c7b87debd4ddac2f8ba8d9b807
if [ ! -d "$checkout/.git" ]; then
  git init "$checkout"
  git -C "$checkout" remote add origin https://github.com/ggml-org/llama.cpp.git
fi
git -C "$checkout" fetch --depth 1 origin "$commit"
git -C "$checkout" checkout --detach FETCH_HEAD
cmake -S "$checkout" -B "$checkout/build" -DCMAKE_BUILD_TYPE=Release \
  -DGGML_NATIVE=OFF -DGGML_OPENMP=OFF -DLLAMA_CURL=OFF
cmake --build "$checkout/build" --target llama-server -j2
python - <<'PY'
import hashlib, json
from pathlib import Path
for name, expected in json.loads(Path('bundle-sha256.json').read_text()).items():
    if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
        raise ValueError('Bundle checksum mismatch: ' + name)
print('Bundle checksums verified. Follow report/android-guide.md for the measured run.')
PY
