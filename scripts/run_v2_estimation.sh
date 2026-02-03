#!/bin/bash
# Run v2 prompt estimation on datasource_complete.tsv
# Resumable, 500 items per chunk

set -e

cd "$(dirname "$0")/.."

INPUT="inputs/datasource_complete.tsv"
PROMPT="weight-volume.v2.system.txt"
OUTPUT=".local/prompt_results/weight-volume.v2.system/datasource_complete/result.tsv"
LIMIT=500

# Create output directory
mkdir -p "$(dirname "$OUTPUT")"

echo "=== V2 Prompt Estimation ==="
echo "Input: $INPUT"
echo "Prompt: $PROMPT"
echo "Output: $OUTPUT"
echo "Chunk size: $LIMIT"
echo ""

# Run with resume flag
uv run python scripts/weight_volume_newprompt.py \
    -i "$INPUT" \
    -p "$PROMPT" \
    -o "$OUTPUT" \
    -l "$LIMIT" \
    --resume

echo ""
echo "=== Done ==="
echo "To continue, run this script again."
