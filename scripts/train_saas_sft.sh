#!/usr/bin/env bash
# End-to-end SaaS SFT workflow for a local Qwen model.
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:7860}"
DATASET_DIR="${DATASET_DIR:-artifacts/datasets/saas_sft}"
TRAIN_OUTPUT_DIR="${TRAIN_OUTPUT_DIR:-artifacts/checkpoints/qwen25_saas_sft}"
OLLAMA_MODEL_NAME="${OLLAMA_MODEL_NAME:-qwen2.5-saas-sft}"
BASE_MODEL_HF="${BASE_MODEL_HF:-Qwen/Qwen2.5-1.5B-Instruct}"
REPEATS="${REPEATS:-10}"

echo "== Generating SaaS SFT dataset =="
python3 benchmarks/generate_saas_sft_dataset.py \
  --base-url "$BASE_URL" \
  --repeats "$REPEATS" \
  --output-dir "$DATASET_DIR"

echo "== Validating dataset =="
python3 benchmarks/validate_saas_sft_dataset.py "$DATASET_DIR/train.jsonl"

echo "== Training Qwen SaaS SFT adapter =="
python3 benchmarks/train_qwen_saas_sft.py \
  --dataset-path "$DATASET_DIR/train.jsonl" \
  --base-model "$BASE_MODEL_HF" \
  --output-dir "$TRAIN_OUTPUT_DIR"

echo "== Writing Ollama Modelfile =="
cat > "$TRAIN_OUTPUT_DIR/Modelfile" <<EOF
FROM qwen2.5:1.5b
ADAPTER ${TRAIN_OUTPUT_DIR}
TEMPLATE """{{ .Prompt }}"""
PARAMETER temperature 0
EOF

echo "== Creating Ollama model: $OLLAMA_MODEL_NAME =="
ollama create "$OLLAMA_MODEL_NAME" -f "$TRAIN_OUTPUT_DIR/Modelfile"

echo "Done. Trained Ollama model available as: $OLLAMA_MODEL_NAME"
