#!/usr/bin/env bash
# InternNav vendors its own LuminaNextDiT2DModel
# (internnav/model/basemodel/internvla_n1/nextdit_traj.py) with the pre-0.33
# `_set_gradient_checkpointing(self, module, value=False)` signature, so
# diffusers 0.33.1 (upstream requirements/internvla_n1.txt) raises TypeError
# during model construction. Upstream's own requirements/habitat_requirements.txt
# pins diffusers==0.32.2 for the Habitat evaluation path, which is the path this
# experiment reproduces. Move to that published pin rather than editing model code.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
venv/bin/python -m pip install --disable-pip-version-check 'diffusers==0.32.2'
venv/bin/python -m pip freeze > setup/pip_freeze.txt
venv/bin/python -c 'import diffusers,torch,flash_attn,transformers; print(diffusers.__version__,torch.__version__,flash_attn.__version__,transformers.__version__)'
printf '%s\n' DIFFUSERS_PIN_APPLIED
