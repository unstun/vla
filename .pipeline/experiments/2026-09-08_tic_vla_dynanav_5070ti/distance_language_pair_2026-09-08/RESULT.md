# Matched Chinese/English three-meter stop comparison

**Neither language completed the three-meter stop task.** In this fresh pair,
Chinese drove through the 3 m reference without stopping and later deviated
substantially. English turned and traveled opposite the initial heading.
The observed outcomes do not justify ranking general Chinese versus English
capability: there is only one paired scene, and the Chinese trajectory also
differs substantially from the preceding same-instruction trial.

## Inputs and measured results

- Chinese: `向前直走 3 米，然后停下`
- English: `Go straight forward for 3 meters, then stop.`
- Order: Chinese then English, separate fresh processes.

| Measurement | Chinese | English |
|---|---:|---:|
| Run ID | `20260908T163626Z_metric_zh` | `20260908T163626Z_metric_en` |
| Finite `(1,30,2)` predictions | 301 | 301 |
| Largest forward displacement | 13.9600 m | 0.1466 m |
| Final forward displacement | +13.9355 m | -8.4830 m |
| Final cross-track displacement, positive left | +9.8434 m | +1.9037 m |
| Command-anchored sampled cumulative path | 20.2080 m | 9.6096 m |
| Closest distance to the 3 m reference | 0.0636 m | 2.8557 m |
| Final distance to the 3 m reference | 14.7131 m | 11.6397 m |
| Measured speed at first cumulative 3 m crossing | 1.3817 m/s | 1.3823 m/s |
| Qualifying two-second near-target stop windows | 0 | 0 |
| Actual timeline after instruction | 15.0000 s | 15.0000 s |
| Sampled total GPU peak | 14621 MiB | 15276 MiB |

Chinese crossed the forward 3 m reference at timeline offset 2.55 s, with
forward displacement 3.0110 m and lateral displacement 0.0627 m. Its measured
speed was 1.3817 m/s, and desired/applied speed remained 1.5000 m/s. This is
direct evidence of passing the target without a stop, rather than merely
failing to find the intended direction. English never reached forward 3 m.
Both also failed to stop when accumulated path first passed 3 m.

Both benchmark goal flags are false by construction because goal-triggered
termination is disabled. The independent position, speed and command checks
establish task failure. Both completed the fixed 1020-frame observation window;
timeout termination is not counted as policy stopping. Neither benchmark
reported a detected collision; this remains the upstream detector's output,
not proof that subsequent low-speed motion was unobstructed.

## Controls and limits

The authoritative predeclared pair protocol is [pair_plan.json](pair_plan.json).
The inherited `plan.json` retains the preceding metric-probe protocol as source
provenance. Both cases use the same source manifest, checkpoint, scene/start,
20-person setting, scene seed 36, inference seed 36, output camera and metric
criteria. Semantic YAML comparison after removing only the instruction passed.
All 602 actual model calls preserve the respective request verbatim.

The pair extends only allowed text, output captions and analysis routing from
the verified metric probe. All model, robot behavior and benchmark Python files
are byte-identical to that probe. The original goal-stop and automatic-backup
confounds remain disabled, as does periodic traceback dumping. Numeric reference
coordinates are measurement/display-only and are not supplied to the policy.

The stop criterion is forward 3 +/- 0.25 m, cross-track within 0.25 m, measured
planar speed and desired/applied linear commands below 0.05 m/s, measured yaw
and desired/applied angular commands below 0.10 rad/s, continuously for two
simulator-timeline seconds without hold or recovery. Each episode runs the same
34 frame-derived seconds: 15 actual timeline seconds after frame-120 startup.

Initial front-camera RGBs are similar but not identical: mean absolute pixel
difference is 1.04395 on the 0–255 scale. Their hashes are recorded in
[front_and_cleanup_proof.json](comparison/front_and_cleanup_proof.json).
Identical seeds do not guarantee identical rendering or asynchronous schedules.
The previous complete Chinese metric trial ended at -8.4395 m forward
displacement, while this fresh Chinese run ended at +13.9355 m. The cause of that
same-language variation has not been isolated. Do not attribute every paired
trajectory difference uniquely to instruction language, or infer a language
ranking from these two failures.

This metric task is distinct from the earlier vending-machine goal comparison,
where the recorded English episode reached the evaluator threshold and the
Chinese episode did not. Neither observation establishes general multilingual
reliability or accurate metric stopping for the checkpoint.

## Video and verification

- [Side-by-side video](comparison/chinese_english_3m_comparison.mp4): left Chinese,
  right English, 2560x792, 301 aligned frames, 15.05 s at 20 FPS. It uses the
  recorded 0.05 s simulator-timeline intervals after instruction application.
  It is not wall-time inference playback or a real-time performance claim.
- [Chinese original wall-time video](runs/20260908T163626Z_metric_zh/navigation_with_trajectory.mp4)
- [English original wall-time video](runs/20260908T163626Z_metric_en/navigation_with_trajectory.mp4)
- [Trajectory and speed comparison](comparison/metric_language_comparison.png)
- [Full numerical comparison](comparison/comparison.json)

The original overhead pixels are preserved; the comparison adds only a text
legend and stacks recorded frames. Both robots eventually leave the intended
route's fixed camera footprint. Complete measured trajectories are shown in the
plot; no replacement footage hides the out-of-view portions.

All 363 artifacts for each case passed local checks, including raw frames inside
their archives: 726 checks total. Both original videos and the comparison fully
decode, and representative composite frames/plots were visually inspected.
Chinese download needed two retries after SSH disconnects; the final hash checks
passed, with no experiment rerun or missing raw evidence.

Shared source manifest SHA-256:
`102f994d02331a6e98118df7e44e39ae126f7f1a6b03d326a1155f6d6674afa7`.
All 78 package checks and 21 pinned model-asset checks passed. Parent metric
manifest: `cd3d13f7b90114b9ad211f7a97a86a00ab5906c32c6acc575264f38087e8eda2`.
Upstream commit: `9fa6f8b66b9e121d5df5df071297bba8e5353ebb`;
checkpoint SHA-256: `376263f89fad0f42c267d85655019232edc91d36e214e23424804dd4cd42e036`.
Nine targeted tests passed, including verbatim Chinese/English request handling.
Both simulator groups (85106, 85865) exited; GPU returned to 258 MiB / 0%.

Local source of truth is this dated directory; the remote execution copy is
`/home/sun/vla_exec/2026-09-08_tic_vla_dynanav_5070ti/distance_language_pair_2026-09-08`.
No physical robot, training, website or Git commit was involved.

`prepare_pair.py` builds a fresh package from the verified parent and refuses to
overwrite a declared pair. After syncing and source/asset verification,
`run_pair.py` executes the cases sequentially with per-case bounded launchers.
It refuses a previously dispatched pair. Retrieve both run directories plus the
two initial RGB files, then run `python3 compare_pair.py` locally to verify,
analyze and compose the archived frames. Preserve previous run IDs and outputs.
