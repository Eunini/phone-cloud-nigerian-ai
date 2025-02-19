#!/usr/bin/env bash
set -euo pipefail
checkout=${1:?usage: build_llama.sh EXTERNAL_CHECKOUT_DIRECTORY}
commit=6050b467c07a95c7b87debd4ddac2f8ba8d9b807
git init "$checkout"
git -C "$checkout" remote add origin https://github.com/ggml-org/llama.cpp.git
git -C "$checkout" fetch --depth 1 origin "$commit"
git -C "$checkout" checkout --detach FETCH_HEAD
cmake -S "$checkout" -B "$checkout/build" -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF -DLLAMA_CURL=ON
cmake --build "$checkout/build" --target llama-server -j2
