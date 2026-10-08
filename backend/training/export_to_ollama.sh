#!/usr/bin/env bash
# Fuse the QLoRA adapter into the fp16 base, convert to GGUF Q4_K_M and register with Ollama.
# Run from backend/:  bash training/export_to_ollama.sh [model-tag]
# The new tag is NOT made the default until evaluation/evaluate.py shows it beats the current model.
set -euo pipefail
cd "$(dirname "$0")/.."

PY=.venv/bin/python
TAG="${1:-nyayshastra-legal-v2}"
BASE_HF="GSMS-B/Indian-Legal-Qwen2.5-3B"
FUSED=training/fused
LLAMA_CPP=training/llama.cpp

# 1. Fuse adapter into full-precision weights (de-quantize so the GGUF is quantized once, from fp16)
$PY -m mlx_lm fuse --model training/base-4bit --adapter-path training/adapters/nyay-qlora \
  --save-path "$FUSED" --dequantize

# 2. HF safetensors -> GGUF f16 -> Q4_K_M (llama.cpp tools)
if [ ! -d "$LLAMA_CPP" ]; then
  git clone --depth 1 https://github.com/ggml-org/llama.cpp "$LLAMA_CPP"
fi
uv pip install --python $PY -r "$LLAMA_CPP/requirements/requirements-convert_hf_to_gguf.txt" >/dev/null
$PY "$LLAMA_CPP/convert_hf_to_gguf.py" "$FUSED" --outtype f16 --outfile training/nyay-f16.gguf
QUANTIZE=$(command -v llama-quantize || true)
if [ -z "$QUANTIZE" ]; then
  echo "llama-quantize not found: install with 'brew install llama.cpp'"; exit 1
fi
"$QUANTIZE" training/nyay-f16.gguf training/nyay-q4_k_m.gguf Q4_K_M

# 3. Register with Ollama using the same runtime parameters as the production Modelfile
sed "s#^FROM .*#FROM $(pwd)/training/nyay-q4_k_m.gguf#" ollama/Modelfile > training/Modelfile.v2
ollama create "$TAG" -f training/Modelfile.v2
echo "[EXPORT] registered $TAG. Evaluate with: OLLAMA_MODEL=$TAG python evaluation/evaluate.py --mode e2e --limit 50"
