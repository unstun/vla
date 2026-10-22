#!/usr/bin/env bash
set -euo pipefail
R=/home/ubuntu/sun/vla_v288_20261020
python3 "$R/migration/offline.py" freeze
python3 "$R/migration/prepare_matrix.py"
