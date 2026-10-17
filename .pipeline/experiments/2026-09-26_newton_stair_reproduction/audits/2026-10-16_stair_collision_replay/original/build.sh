#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/foxy/setup.bash
cmake -S /audit/source/original -B /audit/build_original -DREFERENCE=/audit/reference -DVERSIONS_ROOT=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions -DCMAKE_BUILD_TYPE=Release
cmake --build /audit/build_original -j4
