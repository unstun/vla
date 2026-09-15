#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p tools
if [ ! -x tools/bin/micromamba ]; then tar -xjf setup/micromamba.tar.bz2 -C tools bin/micromamba; fi
export MAMBA_ROOT_PREFIX="$ROOT/mamba"
tools/bin/micromamba create -y -p "$ROOT/sim_env" -c conda-forge -c aihabitat python=3.9 habitat-sim=0.3.3 headless numpy=1.26.4 requests pillow imageio imageio-ffmpeg scipy
sim_env/bin/python -c 'import habitat_sim; print(habitat_sim.__version__)'
tools/bin/micromamba list -p "$ROOT/sim_env" --explicit > setup/sim_explicit.txt
printf '%s\n' SIM_SETUP_COMPLETE
