# v189 Mac ARM64 verification and original full-route trial

Stage: experiment + analysis. Execution date: 2026-10-13 local / 2026-10-14 UTC.

**Component verification passed; full-route acceptance failed.** Nav2 reported
arrival, but the recorded final held yaw error was 0.377481 rad against the
unchanged 0.25 rad limit. Preserve this trial as a failed full-route gate.

## Verification

The authorized execution cohort is Darwin ARM64 host CPU Newton with the pinned
linux/arm64 ROS 2 Foxy image. The Mac native binary underlay is v176, whose
649 source inventory entries exactly match the v177/v188 semantic baseline.
v189 overlays only its four prepared native files. v188 remains the manifest
parent. No remote GPU experiment was launched.

| Check | Observed result |
|---|---|
| Archived environment | All 11 tarballs match remote SHA-256; 98,295,802 compressed bytes restored |
| Build | Two packages rebuilt; 14 native packages available via verified ament prefixes |
| Controller package | 46 unique GTest cases passed: 44 controller, 1 tracking parity, 1 executor shutdown |
| Colcon summary | 49 entries, 0 errors, 0 failures, 0 skipped; includes 3 CTest wrappers |
| Route-heading regressions | 7 named cases in the current source, all passed |
| Generated profile | 2 Python tests passed, including both base-frame configurations |
| Native probes | V176_TERMINAL_CAPTURE_PASS and V189_CORNER_LOOKAHEAD_PASS |
| Mac host | 23 tests passed, 0 failures/errors/skips, including actual managed retention chain |
| Extra container checks | 9 gateway tests, native degenerate-PCT regression, 3 Linux socket tests passed |
| Live graph | Actual v189 controller .so, v172 BT .so and v174 PCT extension observed in process maps |
| Runtime profile | finish_dist=0.02; route_lookahead_heading_enabled=true; route_lookahead_dist=0.5 |
| Host imports/inputs | Physics module imported; 36 pinned inputs verified with no physics advanced |
| Actual receipt gate | Passed before freeze; checks image and all 3,187 source/install file hashes |
| Freeze | 4,195 current/snapshot source pairs and 618 runtime inputs verified |

Evidence: [quality](quality.json), [native receipt](verification/v189_native_receipt.json),
[test log](verification/v189_native_build.log), [host tests](verification/v189_host_tests.json),
[loaded libraries](verification/v189_overlay_loaded.json),
[graph preflight](verification/v189_native_graph_preflight.json),
[actual gate](verification/native_gate_preflight.json), and [manifest](manifest.json).
The quality receipt includes native_packages_available=14, which v184 omitted.
v184 attempt01 was rejected by the episode package-count check before physics;
its frozen source and failure evidence remain unchanged.

## Trial

`v189_mac_full_attempt01` ran the original `historical_full` spatial start and
goal in `building_full`, with factory PD startup, stance hold and continuous
recording from zero physics steps. It reached a Nav2 terminal arrival and the
driver requested `FINISHED` after measured PD hold. The stronger frozen
full-route verifier rejected the final held yaw. No acceptance threshold,
controller source or frozen evidence was changed after seeing the result.

| Measurement / gate | Result |
|---|---|
| Full-route acceptance | **FAIL: final held yaw** |
| Nav2 action / driver | Arrived / execution_completed=true, route_arrived=true |
| Episode process / managed launcher | Exit 0; no timeout; retention completed |
| Physics endpoint / recorded states | 187.680862 s / 8,953 continuous states |
| Navigation interval | 176.660039 simulated s / 212.748508 wall s |
| Actual navigation RTF | 0.830370 |
| Final XY error | 0.138237 m; passes the original position check |
| Desired yaw / final held yaw | -1.861342 / -2.238823 rad |
| Final yaw error / tolerance | **0.377481 / 0.25 rad** (21.63 / 14.32 degrees) |
| Final control | FIXED_STAND; policy_owns_joints=false |
| Fall / state copyback | No fall reported / byte verification passed |
| Replacement owners | 20; all 20 have recorded measured-stop proof |
| Native planning | 3,993 completed rounds; 3,818 successful; 17.946 successful rounds per wall second |
| Raw retention | 1,768 members, 514,787,438-byte verified raw_capture.zip |

Evidence: [outcome](results/v189_mac_full_attempt01/outcome.json),
[full-route rejection](results/v189_mac_full_attempt01/full_route_verification.json),
[final-pose audit](results/v189_mac_full_attempt01/final_pose_audit.json),
[recovery proofs](results/v189_mac_full_attempt01/recovery_proofs.json),
[metrics](results/v189_mac_full_attempt01/metrics.json),
[process](results/v189_mac_full_attempt01/process.json),
[retention](results/v189_mac_full_attempt01/retention_result.json), and
[copyback](results/v189_mac_full_attempt01/state_copyback.json).

`outcome.arrived=false` means the full recorded-route gate failed; it does not
erase the separately recorded Nav2 arrival. The component receipt's
`full_navigation_accepted=false` remains frozen. Stop-proof success establishes
replacement handoff evidence, not final yaw acceptance. This single Mac trial
does not establish repeated reliability, a sustained 30 Hz planner, an exclusive
cause for the yaw discrepancy, or cross-host performance. No second attempt or
controller repair was run.

The next bounded investigation is the final-goal yaw/hold transition using this
capture, before proposing a new integer version. Execution identity comes from
this run's `episode_request.json` and metrics; `full_route_input.json` preserves
the inherited spatial fixture, including historical host/native descriptive
labels that are not this run's execution identity.

## Reproduction and storage

Restore the archives listed in [environment_archives.json](verification/environment_archives.json)
from `gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_20261012/environment/`
into `/private/tmp/vla_stop_audit_20261012`, extracting in version order. Preserve
the original archive names and verify against the remote SHA-256 list.
`prepare_native.py` resolves archive-omitted inherited source only through exact
hash matches in those restored workspaces.

With Docker Desktop running, execute the following from the repository root:

```sh
V189=.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v189
PY=.pipeline/experiments/2026-09-26_newton_macos_policy/runtime/.venv/bin/python
TASK=/private/tmp/vla_stop_audit_20261012
$PY "$V189/build_mac.py" --task-root "$TASK"
$PY "$V189/test_overlay_runtime.py" --task-root "$TASK"
$PY "$V189/verify_mac_host.py" --output "$TASK/evidence/v189_host_tests.json"
$PY "$V189/freeze_host.py" verify
$PY "$V189/run_mac_full.py" --task-root "$TASK" --attempt 2
$PY "$V189/close_mac_trial.py" --trial "$TASK/v189_mac_full_attempt02"
```

Build/preflight output paths are intentionally exclusive; use a freshly restored
environment for rebuilding. Do not overwrite the frozen quality, manifest,
source or an existing attempt. A rebuilt receipt must match the frozen receipt
exactly to qualify under this version. The commands describe a separately
authorized future repeat; this task runs attempt01 only.

Closed raw evidence and the qualified Mac environment are archived at
`gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v189_20261013/`:

- `v189_mac_full_attempt01.tar`: 622,202,880 bytes, SHA-256
  `3ac47891c7682eb54dd6ad539f33e564f6526036584cc471cd9998785cba4e73`.
- `v189_qualified_mac_environment.tar.gz`: 8,677,038 bytes, SHA-256
  `0c09461b046c935ee1f210da471854bba5fd9fe38cde0d8838d381118e1f8208`.

Both remote archive hashes passed; all 293 trial archive file/symlink members
were individually verified remotely. [Archive verification](results/v189_mac_full_attempt01/archive_verification.json)
and [ARTIFACTS.json](results/v189_mac_full_attempt01/ARTIFACTS.json) record locations,
member manifests, source identity, retrieval and restore instructions. The
qualified-environment archive restores the tested receipt and binaries over the
11 base archives; it avoids substituting a newly rebuilt receipt. Local originals
remain intact, and all owned trial containers have stopped.

Post-run freeze verification passed (4,195 source pairs, 618 runtime inputs).
All 1,562 existing files and the path set under v177-v188 are unchanged, and the
four prepared native files retain their declared hashes. See
[source preservation](results/v189_mac_full_attempt01/source_preservation.json).
No commit was made. Raw data and build products stay outside the repository;
only compact results, verification records and frozen source are added here.
