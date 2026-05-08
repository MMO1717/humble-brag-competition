#!/bin/bash
set -e

echo "=== BRAG-Agent v6 Test Submission ==="
echo ""

echo "[1/2] Running test submission..."
python run_multi_agent_official.py \
  --input BRAG-Agent-public/data/test_input.jsonl \
  --output outputs/test_submission.jsonl \
  --concurrency 3

echo ""
echo "[2/2] Running format checker..."
python BRAG-Agent-public/scripts/format_checker.py \
  outputs/test_submission.jsonl \
  BRAG-Agent-public/data/test_input.jsonl

echo ""
echo "=== Done ==="
echo "Output: outputs/test_submission.jsonl"
