# Evidence source index for the OmniVLA VLA audit

This note is a routing index, not an audit result. Re-open the cited source
before making a claim and preserve the current line anchors in the final code
trace.

## Pinned upstream and surveyed interface

Source:
`.pipeline/survey/2026-08-16_lite3_vla_open_source_reproduction_survey.md`

- Lines 168-180: paper/project identity, pinned source commit, and license
  boundary.
- Lines 182-186: supported goal modalities and the `8 x [x,y,hx,hy]` action
  representation.
- Lines 202-218: official original/edge entry points and expected observable
  outputs.
- Lines 220-228: known prompt-sensitivity, scale, clipping, and Lite3-adapter
  risks.
- Lines 373-375: why prompt sensitivity, scale, curvature, and collision audit
  are first-stage tests rather than assumed properties.
- Lines 393-397: receive-only minimal reproduction goal and excluded claims.
- Lines 457-477: required raw evidence and the original minimum input-sensitivity
  proposal.

## OmniVLA-original runtime path

- `deploy/omnivla_lite3_receive_only/engine_original.py:68`: decode the request
  JPEG into RGB.
- `deploy/omnivla_lite3_receive_only/engine_original.py:70-78`: pass current
  image and instruction into upstream preprocessing.
- `deploy/omnivla_lite3_receive_only/engine_original.py:79-96`: invoke the
  pinned forward path with the action head.
- `deploy/omnivla_lite3_receive_only/engine_original.py:97-103`: record modality,
  require `(1,8,4)`, and return the trajectory.
- `third_party/2026-08-18_omnivla_5182600/OmniVLA/inference/run_omnivla.py:386-410`:
  upstream image/language batch transformation.
- Same file lines 411-476: modality selection, VLA hidden-state generation,
  action-head prediction, and returned action trajectory.

## OmniVLA-edge runtime path

- `third_party/2026-08-18_omnivla_5182600/OmniVLA/inference/run_omnivla_edge.py:154-180`:
  load/resize current image and tokenize the exact language prompt.
- Same file lines 308-339: select modality ID, encode text with CLIP, pass text
  and current image to the edge model, and return predicted actions.
- `third_party/2026-08-18_omnivla_5182600/OmniVLA/inference/model_omnivla_edge.py:211-217`:
  accept `feat_text` and `current_img`, then fuse them through the FiLM path.
- Same file lines 278-284: reshape the action predictor output into the
  trajectory dimensions.

## Existing observed boundaries

- `.pipeline/experiments/2026-08-19_omnivla_lite3_receive_only/README.md:36-54`:
  one real Lite3 image/instruction original-model run and timing observation.
- Same file lines 84-90: explicit receive-only claim boundary.
- `.pipeline/experiments/2026-08-19_omnivla_edge_orin64/README.md:12-21`:
  edge receive-only safety and claim boundary.
- Same file lines 62-78: accepted Orin run identity, forward/wall time, and
  cleanup evidence.

## Interpretation guard

These sources can establish pinning, code connectivity, and prior single-run
observations. They do not by themselves establish causal learned use of either
input, semantic instruction compliance, navigation reliability, collision
avoidance, Lite3 metric calibration, or safe actuation.
