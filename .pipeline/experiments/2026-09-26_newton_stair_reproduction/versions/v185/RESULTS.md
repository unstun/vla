# v185 result: rejected after five complete-route attempts

Stage: experiment and analysis. Keep this frozen version and all failed captures.
Do not promote it over the prior baseline. Same original Building map/start/goal,
RL weights and physics; gpu5070ti CPU Newton with AMD64 Foxy navigation.

| Attempt | Arrival | Recorded physical time (s) | Measured path (m) | Longest terminal crawl under the declared metric (s) |
|---|---:|---:|---:|---:|
| 01 | yes | 120.186 | 76.718 | 0 |
| 02 | no | 71.392 | 23.449 | 2.219 |
| 03 | no | 84.005 | 35.344 | 0 |
| 04 | yes | 140.469 | 77.134 | 0 |
| 05 | yes | 120.405 | 76.342 | 0 |

All30 replacement owners across the five attempts have recorded measured-stop
proof (4,7,7,10,2 respectively). Neither failed attempt fell. In both,
six successive later owners lacked a trajectory and exhausted recovery. The
last zero-command intervals lasted21.408s and22.708s; neither is nonzero-command
endpoint crawling. Attempt02 also retains a separate2.219s terminal crawl flag.

The actual model-input audit verifies24,075 frames, including the newest
command and complete command history, with zero discrepancy and no telemetry
gaps. The audit source, per-attempt metrics and thresholds are under
`audits/2026-10-13_v185_terminal_capture/`. Estimated curve phase is not an exact
replay of the controller clock. The source change cannot be called the exclusive
cause of the two route failures without a paired physical counterfactual.

Native checks:39 unique controller gtest cases (42 colcon result entries),
recorded terminal command regression,2 generated-profile cases,18 host tests,
and actual controller/BT/PCT loaded-library inspection passed. These component
results did not predict full-route reliability. The local3cm immediate-capture
approach is shelved; v186 restores2cm and tests progress-aware terminal release.

Full raw captures remain at
`gpu5070ti:/data/sun/vla_mppi_20261009/trials/v185_full_candidate_attemptNN/`.
Each locally returned `results/full_repeats/.../remote_artifacts.json` records
all293 files/symlinks and SHA-256. Failed attempts02/03 remain alongside passes.
