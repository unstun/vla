#!/usr/bin/env bash
# Swap habitat-lab 0.3.3 for the v0.2.4 candidate inside the cloned evaluator env.
#
# official_env      : untouched habitat-lab 0.3.3 record (kept as the failed-version evidence)
# official_env_024  : byte copy of the above; habitat-lab/habitat-baselines replaced by v0.2.4
#
# habitat-sim stays at the already-verified 0.3.3 conda build. Whether habitat-lab
# 0.2.4 can drive habitat-sim 0.3.3 is exactly what the preflight has to establish.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV024="$ROOT/official_r2r/official_env_024"
SRC024="$ROOT/official_r2r/src/habitat-lab-024"
PY="$ENV024/bin/python"

echo "== interpreter =="
"$PY" -c 'import sys; print(sys.version); print(sys.prefix)'

echo "== remove habitat-lab 0.3.3 editable installs =="
"$PY" -m pip uninstall -y habitat-lab habitat-baselines 2>&1 | tail -5

echo "== install habitat-lab v0.2.4 (no deps) =="
"$PY" -m pip install --no-deps --no-build-isolation -e "$SRC024/habitat-lab" 2>&1 | tail -5
"$PY" -m pip install --no-deps --no-build-isolation -e "$SRC024/habitat-baselines" 2>&1 | tail -5

echo "== versions =="
"$PY" - <<'PYEOF'
import habitat, habitat_sim, habitat_baselines
print('habitat', habitat.__version__, habitat.__file__)
print('habitat_baselines', habitat_baselines.__version__, habitat_baselines.__file__)
print('habitat_sim', habitat_sim.__version__)
PYEOF

echo "== freeze =="
"$PY" -m pip freeze > "$ROOT/public_scenes/setup/env_024_pip_freeze.txt"
echo ENV024_SETUP_COMPLETE
