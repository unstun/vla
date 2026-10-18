#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/command_continuity_v206_20261015/install/setup.bash
source /task/starvation_recovery_v219/install/setup.bash
source /task/callback_failure_v232/install/setup.bash
source /work/install/setup.bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
version=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v240
test ! -e /work/publication_contract01
mkdir /work/publication_contract01
cmake -S "$version/contracts" -B /work/probe_publication_contract01 -DVERSIONS_ROOT="${version%/v240}" -DCMAKE_BUILD_TYPE=Release > /work/publication_contract01/configure.log 2>&1
cmake --build /work/probe_publication_contract01 -j2 > /work/publication_contract01/build.log 2>&1
export REPLAY_INPUT=/task/terminal_approach_v238/input05 CONTRACT_OUTPUT=/work/publication_contract01
/work/probe_publication_contract01/publication_contract --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level error > /work/publication_contract01/run.log 2>&1
