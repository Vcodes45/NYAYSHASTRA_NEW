#!/usr/bin/env bash
# QLoRA fine-tuning of the legal SLM on Apple Silicon with mlx-lm.
# Run from backend/:  bash training/train_mlx.sh
set -euo pipefail
cd "$(dirname "$0")/.."

PY=.venv/bin/python
BASE_HF="GSMS-B/Indian-Legal-Qwen2.5-3B"   # merged safetensors of the GGUF currently served by Ollama

$PY -c "import mlx_lm" 2>/dev/null || uv pip install --python $PY -r training/requirements-train.txt

# 1. Grounded instruction data (document-level split, benchmark sections held out)
$PY training/generate_instruction_data.py

# 2. 4-bit base for QLoRA (one-off)
if [ ! -d training/base-4bit ]; then
  $PY -m mlx_lm convert --hf-path "$BASE_HF" --mlx-path training/base-4bit -q --q-bits 4 --q-group-size 64
fi

# 3. Train (validation loss is reported every steps_per_eval; checkpoints every save_every)
$PY -m mlx_lm lora --config training/lora_config.yaml 2>&1 | tee training/train.log

# 4. Held-out test loss / perplexity
$PY -m mlx_lm lora --model training/base-4bit --adapter-path training/adapters/nyay-qlora \
  --data data/mlx --test 2>&1 | tee training/test.log

cp training/lora_config.yaml training/adapters/nyay-qlora/
cp manifests/dataset_manifest.json training/adapters/nyay-qlora/ 2>/dev/null || true
echo "[TRAIN] adapter saved to training/adapters/nyay-qlora"
