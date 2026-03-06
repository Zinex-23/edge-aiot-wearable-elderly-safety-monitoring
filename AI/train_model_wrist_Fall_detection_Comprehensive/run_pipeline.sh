#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 prepare_train_ready.py
python3 train_model.py

echo "Pipeline completed."
