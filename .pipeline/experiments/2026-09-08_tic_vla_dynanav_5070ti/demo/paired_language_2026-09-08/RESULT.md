# Matched Chinese/English instruction pair

Both full instructions include going straight and stopping at the vending
machine. The Chinese episode failed; the English episode reached the original
1.5 m evaluation radius. This is one exploratory pair, not a statistical estimate
or proof of the root cause.

| Condition | Chinese | English |
|---|---|---|
| Run | `20260908T153532Z_615007` | `20260908T153918Z_f89862` |
| Verbatim instruction | 直走，并在自动售货机前停下 | Go straight ahead and stop at the front of the vending machine. |
| Goal result | Failed at scenario limit | Reached evaluation radius |
| Final goal error | 19.0298 m | 1.4946 m |
| Reported physical collision | Yes | No |
| Model calls | 461 | 184 |
| Finite `(1,30,2)` outputs | All | All |
| Video wall-clock duration | 108.16 s | 33.04 s |
| Local artifact checks | 723 passed | 246 passed |

## Controls and verification

- The pair was declared in `plan.json` before launch, including order (Chinese,
  English), exact strings and seed 36 for both scenario and inference.
- Both fresh processes used source manifest
  `4a940f97a40d7cb513efd044f7df707daf71a13073f303b7395a4f050832c8c0`.
  Parsed scenario objects match after removing only the instruction field:
  same hospital, start `[-3,-1.2,0.01]`, yaw 0, goal `[9.72,2.33,0.01]`, 20 people,
  70-second frame-derived limit, 1.5 m threshold and top-down recording.
- The request, metadata, scenario, evaluator and every model-call audit agree on
  the exact text. Both stdout logs confirm `TICVLA_INFERENCE_SEED 36` was applied
  after the initial model-cache reset. The upstream stochastic generation
  parameters were not changed.
- Frame 120 of each original front camera visibly contains the vending machine
  under very similar scale and occlusion conditions. The images are not byte
  identical; their mean absolute RGB difference is 1.336 on a 0–255 scale.
  Four initial/early front images were copied and matched to remote hashes.
- Both videos decoded successfully and representative views were inspected. All
  archived raw overlay frames and packaged artifacts passed SHA-256 checks.
- Both recorded simulator process groups exited; the final GPU sample was
  258 MiB used, 0% utilization. No live stream or website was started.

## Interpretation and limits

Adding the omitted straight/stop wording did not rescue this Chinese episode,
while the matched English episode succeeded under the same configured conditions.
Initial total visual occlusion is not supported by the camera evidence. These
observations make instruction/target/action alignment a useful next diagnosis
target, but do not establish that Chinese alone caused the difference or that
the checkpoint cannot handle any Chinese instruction.

The first generated English description names a vending machine. The Chinese
description instead targets a workstation/desk. This is a diagnostic clue, not
independent evidence of internal model understanding.

Only one run per full-language condition was executed. Rendering, asynchronous
generation and GPU execution are not guaranteed deterministic, even with matching
seeds. Distance and pedestrian occlusion were not independently varied in this
pair. The Chinese robot leaves the fixed camera's intended route footprint;
the full recording is retained rather than cropped/spliced to hide this.

Use `comparison.json`, `initial_rgb_comparison.json`, `front_remote_hashes.json`,
`execution.json` and each run's original artifacts for exact evidence. Recompute
the checks with `python3 compare_pair.py`; `run_pair.py` refuses to overwrite an
existing execution record. No training, checkpoint modification or Git commit
was performed.
