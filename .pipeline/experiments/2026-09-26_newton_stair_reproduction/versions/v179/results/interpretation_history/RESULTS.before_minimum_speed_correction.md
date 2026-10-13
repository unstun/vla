# v179 policy-only stop diagnosis

Stage: experiment + analysis. Twelve varied scripted conditions completed on
Mac ARM64, six flat and six in the original Building stair scene, with the same
current V12-derived ONNX policy and v177 physics/controller contracts.
Navigation was disconnected. Automatic stance control was detached after the
original factory-to-policy REJOIN; all24zero-command windows were verified
policy-only with Kp20/Kd0.5 and the declared command actually entering inference.

## Result

The stop-drift symptom occurs without navigation. Four of12flat stop windows
and seven of12stair-scene stop windows exceed the predeclared5cm late-excursion
flag. This flag is diagnostic, not an industry safety criterion. Each window
contains500control steps (nominal10s); the first2s are excluded from the late
metric. Repeated conditions within a run are not independent statistical trials.

Flat maximum late excursion:31.15cm; maximum command-to-end displacement60.81cm.
Stair-scene maximum late excursion:14.54cm; maximum command-to-end displacement
31.92cm. Late maximum excursion and endpoint displacement are different metrics.
All12second walking segments moved0.49–1.38m in3s; scripts completed and none
triggered the declared up-vector fall abort. This does not qualify stopping.

| Run | Stop1 late maximum, cm | Stop2 late maximum, cm | Larger stop endpoint displacement, cm | Restart net XY, m |
|---|---:|---:|---:|---:|
| v179_flat01 | 6.3 | 2.6 | 5.1 | 0.740 |
| v179_flat02 | 9.4 | 31.2 | 60.8 | 0.614 |
| v179_flat03 | 3.3 | 1.7 | 6.0 | 1.032 |
| v179_flat04 | 2.4 | 6.3 | 19.6 | 1.061 |
| v179_flat05 | 2.0 | 1.7 | 5.8 | 1.335 |
| v179_flat06 | 3.0 | 2.0 | 8.3 | 1.346 |
| v179_stairs01 | 14.5 | 6.0 | 31.9 | 0.494 |
| v179_stairs02 | 6.8 | 5.0 | 20.5 | 0.518 |
| v179_stairs03 | 5.7 | 1.5 | 7.4 | 1.046 |
| v179_stairs04 | 5.9 | 1.5 | 12.7 | 0.919 |
| v179_stairs05 | 5.6 | 2.5 | 6.6 | 1.075 |
| v179_stairs06 | 3.0 | 5.9 | 10.8 | 1.377 |

## Interpretation and limits

This establishes a limitation in the current policy/deployment/physics chain,
not a proof that training alone is the root cause. No cross-simulator or hardware
comparison was performed. The earlier V12 command-generation and reward findings
remain source-level leads. No retraining or stop-controller repair was performed.

The stairs condition includes a flat approach and the first stair flight. The
slow first stops in attempts01–02 begin before the first riser; these must not
be called12independent mid-stair stops. Later stops occur on raised treads and
transitions, confirmed by recorded foot positions and body elevation. The
cohort does not establish arbitrary stair-pose stopping.

Foot forces and world positions were recorded50Hz. Persistent-contact motion
uses force>5N at both sample endpoints; unloaded fractions and finite-difference
speeds are descriptive. They do not uniquely distinguish policy-initiated steps,
contact jitter or passive sliding. Videos must be inspected alongside them.

## Verification and storage

Six schedule/analysis tests pass. The unchanged golden policy check passes1000
frames, maximum action error0.00598145 against its existing0.01tolerance. Runtime
observation-coordinate and applied-force checks remain active. Source/snapshot
identity verifies135files. Peak child RSS was841924608bytes. The remote host was
not admitted for simulation because other jobs were active; all physics is Mac,
not a Linux repeat. No remote tasks were stopped.

All12raw archives are durably stored under
`gpu5070ti:/data/sun/vla_mppi_20261009/policy_stop_v179_mac/archives/`.
Every archive and all13members per run were SHA-verified remotely. Exact receipt,
file size/hash and source location: `results/raw_receipts/`. Raw local captures
remain at `/private/tmp/vla_policy_stop_20261012/runs/`; no unique evidence deleted.
`results/summary.json` and `results/stops.csv` retain all24windows.

Reanalysis: restore the verified archive members into an empty declared run
directory, then run this version's `analyze.py --runs <parent> --output <new>`
with the pinned NumPy environment. Verify `freeze.py verify` before execution.
Display source is separately versioned; v180's initial Retina caption layout
failed visual review and is retained. v181 corrects display only.

## Training-speed configuration follow-up

The archived `model_149999` handoff `tracked_configs/env.yaml` was subsequently
read and hashed in `results/training_command_config.json`. Its curriculum raises
the global forward/backward command bound from0.5m/s to1m/s at20kiterations and
2m/s at50k. The terrain-specific cap is2m/s on flat and1m/s on stairs. Lateral
cap is1m/s; yaw caps are2rad/s on flat and1.5rad/s on stairs. These are configured
limits, not measured achieved velocities or a sampled training histogram.

The tested0.2/0.35/0.5m/s commands are within those bounds, but the dynamic
command sampler also imposes a remaining-distance/time lower bound. Range
membership cannot establish frequent training exposure to each low speed or
true stationary command. The present cohort diagnoses navigation-relevant low
speeds, not performance over the policy's full configured speed range.
