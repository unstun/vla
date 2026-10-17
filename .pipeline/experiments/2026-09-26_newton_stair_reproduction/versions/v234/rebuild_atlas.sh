#!/usr/bin/env bash
set -eo pipefail
versions=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions
cmake -S "$versions/v224/tools" -B /work/export_build -DVERSIONS_ROOT="$versions" -DCMAKE_BUILD_TYPE=Release
cmake --build /work/export_build --target export_field -j2
export REPLAY_INPUT=/work/fixtures/building
export STATIC_PCD=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/inputs/static_background/building2_9.pcd
export ENVIRONMENT_OUTPUT=/work/fixtures/building/environment03.env
/work/export_build/export_field --ros-args --params-file /work/fixtures/building_planner.yaml --log-level error
python3 - <<'PY'
from pathlib import Path
import hashlib
assert hashlib.sha256(Path('/work/fixtures/building/environment03.env').read_bytes()).hexdigest() == '72142fda10deec9cfabab95f5d27d1159fa8ec3821f1a808f4a6a1f8186edaac'
PY
cmake -S "$versions/v225/tools" -B /work/atlas_build -DVERSIONS_ROOT="$versions" -DCMAKE_BUILD_TYPE=Release
cmake --build /work/atlas_build --target build_atlas -j2
export RAW_FIELD=$ENVIRONMENT_OUTPUT RAW_FNV=4316416882194453309
export ATLAS_OUTPUT=/work/fixtures/building/environment225.env
/work/atlas_build/build_atlas
python3 - <<'PY'
from pathlib import Path
import hashlib
assert hashlib.sha256(Path('/work/fixtures/building/environment225.env').read_bytes()).hexdigest() == '7ec06542ef9e2451fe63e89a3baf24d225aa3efcbe5ea025c287eb1b67bbdd84'
print('EXACT_ENV225_RECONSTRUCTION_PASS physics_steps=0')
PY
