# v194 Mac attempt 01: original full-route gate passed

Stage: experiment + analysis. Executed 2026-10-14. **FINISHED,
route_arrived=true, full_route_verification.passed=true.** This is one continuous
Mac ARM64 CPU Newton trial with the frozen v194 ARM64/Foxy native overlay.
It validates this declared original-route attempt, including final PD hold and
pose tolerances. Repeated reliability, sustained 30 Hz, general collision
clearance and real-robot performance remain unvalidated.

This report is separate because `v194/RESULTS.md` is itself a frozen source file
(SHA-256 `dbe203f3f9787800276d95e15e6c19ac367ee19c945d295616d7dd9fa68fe663`).
That file remains the historical component/graph qualification record. Updating
it would violate the requested freeze guardrail. The current version index
links to this trial report.

## Execution and acceptance

The requested interpreter path did not exist and exited 127 before creating an
attempt. Execution then used the existing environment specified by the frozen
launcher, under `vla/.pipeline/experiments/2026-09-26_newton_macos_policy/`.
The launcher and arguments were unchanged; exactly one physics attempt ran.
See [execution provenance](execution_provenance.json).

The frozen `close_mac_trial.py` ran its original analysis and full-route
verifier. All original-start/goal, zero-step initial-frame, continuous-state,
no-fall, arrival, final PD hold, XYZ/yaw and shared-state checks passed.
The independent supplemental pose calculations agree with the frozen verifier.
All three observed PCT publications preserved the exact same terminal Pose.

| Measurement | Observed value |
|---|---:|
| Terminal / driver arrival / driver completion | FINISHED / true / true |
| Frozen full-route gate / outcome qualification | PASS / true |
| Accumulated 3D body path, sensor samples | 77.034073670 m |
| Accumulated 3D body path, recorded states from startup | 78.153521319 m |
| Final XY error / tolerance | 0.121167851 / 0.25 m |
| Final reference-height error / tolerance | 0.006756115 / 0.20 m |
| Final yaw error / tolerance | 0.104157523 / 0.25 rad |
| Recorded physics endpoint, including startup | 137.528274536 s |
| Navigation simulation / wall interval | 126.507451057 / 126.540359958 s |
| Actual navigation RTF | 0.999739934 |
| Managed child wall / launcher wall | 169.681417292 / 195.409782209 s |
| Successful local planning / direct controller output | 23.676240537 / 29.811494710 wall Hz |
| Completed / successful planning rounds | 3,122 / 2,996 |
| Planning-round median / p95 / p99 / maximum | 6.486271 / 35.264173 / 210.974611 / 402.826125 ms |
| Planning rounds over 100 ms / over 1 s | 87 / 0 |
| PCT route / B-spline publications | 3 / 3,005 |
| Recorded states / largest consecutive position step | 6,463 / 0.048459629 m |
| Final control / policy joint ownership | FIXED_STAND / false |
| Reported falls / dropped physics steps | 0 / 0 |
| Shared-state verification / retained-byte checks | PASS / PASS |

Final body XYZ is `[2.0475287437, -2.9089541435, 4.8262743950]` m. Height error
is measured against the original goal ground Z plus the fixed 0.30 m reference
body height. The two path lengths use different sample streams; they must not
be mixed. Navigation wall time excludes factory startup and closure; the
managed-child and launcher wall measurements cover wider execution intervals.

## Recovery and remaining limitations

There were **9 entries into EMERGENCY_STOP, 9 exits, and 10 repeated
EMERGENCY_STOP-to-EMERGENCY_STOP transitions**. The frozen analyzer's
`emergency_transitions=19` includes those 10 self-transitions. These are planner
state transitions, not 19 independent recoveries or physical-stop proofs.

Nav2 logged one `Failed to make progress` error and **one completed 1-second
Wait recovery**, then ultimately logged `Navigation succeeded`. No spline-wait
timeout or invalid sampled-trajectory error occurred. Thus this run exercises
recovery after a progress failure, but does not physically exercise the new
spline-wait timeout branch. The low-speed sensor intervals lasting at least
one second were 64.296295–74.490692 s (10.194397 s), 132.593582–133.802078 s
(1.208496 s), and 134.003494–137.528275 s (3.524780 s). The last interval includes
the terminal hold; these intervals are not all navigation failures.

Direct cmd_vel had **17 nonzero-to-zero transitions, 16 subsequent restarts,
and 9.422262201 wall seconds of recorded zero-command exposure**. Initial zeros
are excluded and the last unrestarted zero ends at the last recorded command.
Option B has no P2B measured-stop proof protocol: proof counts and
cancel-to-proof waiting are not applicable, rather than zero. A zero command,
an emergency-state exit, and a completed Wait do not each prove a stationary
physical body. Final measured PD hold passed its separate gate.

Successful local planning averaged below 30 Hz, with 87 rounds longer than
100 ms. Near-unit RTF and the passed arrival gate do not establish sustained
30 Hz or eliminate route pauses. No source repair or second physical attempt
was made after observing these results.

## Comparison with retained Mac attempts

| Measurement | v189 attempt 01 | v192 attempt 01 | v194 attempt 01 |
|---|---:|---:|---:|
| Terminal | FINISHED | FAILED | FINISHED |
| Driver route arrival | true | false | true |
| Full-route gate | FAIL: held yaw | FAIL: no arrival | PASS |
| Sensor-sampled body path, m | 77.816013461 | 72.572288516 | 77.034073670 |
| Final XY error, m | 0.138237115 | 4.832351783 | 0.121167851 |
| Final height error, m | 0.015110302 | 0.008518028 | 0.006756115 |
| Final yaw error, rad | 0.377481246 | 0.525199548 | 0.104157523 |
| Total recorded simulation, s | 187.680862427 | 118.886291504 | 137.528274536 |
| Navigation simulation, s | 176.660038948 | 107.865468025 | 126.507451057 |
| Navigation wall, s | 212.748508333 | 117.584897625 | 126.540359958 |
| Navigation RTF | 0.830370282 | 0.917341174 | 0.999739934 |
| Successful local planning, wall Hz | 17.946071772 | 26.066272641 | 23.676240537 |
| Observed controller output, wall Hz | 24.562429855 | 29.984195176 | 29.811494710 |
| Maximum planning round, ms | 625.186917 | 774.569792 | 402.826125 |
| Logged emergency transitions, including repeats | 82 | 17 | 19 |
| Completed stock Wait recoveries | N/A | 6 | 1 |
| Spline-wait timeouts | N/A | 7 | 0 |
| P2B measured-stop proofs / waiting, s | 20 / 34.225421601 | N/A | N/A |

v189's controller observation is `/quad_0/raw_scan_cmd_vel`; its gateway
`/quad_0/cmd_vel` measured 34.194978017 Hz and is a different stream. v192/v194
use direct `/quad_0/cmd_vel`. v192's endpoint errors describe its last recorded
pose without arrival or final hold. Its shorter runtime covers an incomplete
route. These are three individual captures with different code and realized
trajectories, not a controlled reliability or causal speed comparison. v194
passes the unchanged yaw gate that rejected v189 and reaches the goal that
v192 did not reach. Exact values and source hashes are in
[comparison.json](comparison.json).

## Preservation and remote archive

The raw trial is archived at:

`gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v194_20261014/v194_mac_full_attempt01.tar`

Size: **445,890,560 bytes**. SHA-256:
`c09b9a3c42338ff11e7598d0a1a7e4fa8d4c64ba56a66027dceaad5b575d7550`.
Remote verification checked the complete TAR digest, all **287 regular files**,
the **one symlink**, and all **1,269 raw ZIP members** against recorded hashes
and sizes. The original raw ZIP is 367,554,566 bytes. A first post-trial verifier
assumed the driver JSON was inside the ZIP; it is an outer TAR file. The helper
was corrected to use the frozen Capture reader's outer-file-first lookup, then
all remote checks passed. The initial helper error is retained and did not
change any trial bytes.

Pre-run and final freeze verification pass for **4,814 source/snapshot pairs
and 618 runtime inputs**. All eight original protected inventories remain
unchanged. An additional complete before/after comparison covers all **3,721
entries in recovery_v194**, including build/install/log paths, bringing the
checked protected roots to nine. No additions, removals or changes were found.
The manifest remains SHA-256
`f9366a28664fe3e5a401672b5829110dec0d7e4ef3c2a94b6cb3ed8075025fd8`.

The trial container was removed by the launcher. Local temporary originals
remain intact; no source, build tree or raw trial was deleted. No review video
was requested or created in this closure.

Evidence: [frozen gate](full_route_verification.json), [metrics](metrics.json),
[supplemental audit](trial_analysis.json), [analysis agreement](analysis_consistency.json),
[terminal log excerpt](terminal_log_excerpt.txt), [remote verification](remote_verification.json),
[artifact and restore record](ARTIFACTS.json), [freeze check](final_freeze_verify.json),
and [protected trees](final_protected_check.json).

For reanalysis, restore the TAR into an empty directory, keep the frozen local
repository available, then use its v194 `analyze_remote.py --run-root RUN
--output NEW_OUTPUT --metrics-only` and `verify_full_route.py --run-root RUN`.
The recorded `analyze_outcome.py` accepts the restored trial directory. Reanalysis
does not rerun physics. Full retrieval commands are in `ARTIFACTS.json`.
