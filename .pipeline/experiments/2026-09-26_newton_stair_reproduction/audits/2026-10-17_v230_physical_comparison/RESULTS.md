# One v230 closed-loop physical comparison: failed

The two approved commits are `420a0ff9` (v229 support-aligned GPMP height)
and `e9f8bec0` (v230 mission-scoped local obstruction feedback). No push was
requested. The single subsequently authorized physical attempt is
`v231_linux_full_attempt01`: v231 binds the execution environment to frozen
v230 navigation; it introduces no navigation algorithm change.

## Outcome

The original full-route gate **failed**. At approximately 46.7 s the controller
logged `A-star error`, `rebound_no_valid_new_constraints`, then
`terminate called without an active exception`. ROS launch recorded
`controller_server` exit code **-6 (SIGABRT)**. See
[exact log context](results/controller_abort_context.txt).
The final reactive observation was at 46.686 s; the exact process-exit physics
timestamp was not recorded. Video failure labeling begins at 47 s.

The upper-level job remained `running`, without a terminal finish request.
Original recording continued to its unchanged 600000-step bound, ending at
600.516541 s actual solver time. No fall occurred; the final body position was
(8.154142, -3.904310, 1.851326), short of the original destination. Measured path
length was 24.083483 m. Navigation pacing RTF was 0.999999, with zero dropped
physics steps. No second physical attempt, tuning, reset or threshold change
was performed.

The missing finish request also makes the original closed shared-state check
fail. The unchanged original analyzer fails on that check, and the full-route
verifier fails with `KeyError('finish_request')`; both failures remain saved.
`diagnostic_metrics.py` reuses the original clock/round parser only for
display metrics, explicitly returns `shared_state_verified=false`, and retains
`full_qualification=false`. This adapter cannot grant physical acceptance.
See [outcome](results/outcome.json), [original gate](results/full_route_verification.json),
[original analyzer failure](results/analysis.log), and
[shared-state receipt](results/execution_receipts/shared_state.json).

## Stair window

| Measurement | v219 reference | v230 navigation / v231 execution |
|---|---:|---:|
| Full-route result | Passed | Failed: controller SIGABRT |
| Completed local rounds starting in [45,55) | 208 | 42 |
| Successful completed rounds | 118 (56.73%) | 42; only an early prefix |
| Last completed round start in the window | 54.951427 s | 46.376141 s |
| Incomplete round starts | 0 | 1, at 46.411121 s |
| Completed rounds starting in [47,55) | 200 | 0 |
| Measured low-speed intervals overlapping window | 1 | 1 |
| Low-speed overlap within [45,55) | 3.298187 s | 7.794315 s |

The new 42/42 proportion is **not a 100% success rate across the stair window**:
the controller stopped providing rounds after the early prefix. The v219 pause
was 46.905849–50.204037 s. The new pause began at 47.205685 s and continued to
600.438416 s (553.232731 s total). Pause means measured XY speed below
0.05 m/s, valid sensor intervals below 0.5 s, and an entire interval of at least
1 s. See [per-second coverage, stance states and pauses](results/comparison.json).

## Body edge margin

Both recordings were evaluated against the **same frozen ENV225 field**, using
actual body XYZ and quaternion-derived planar yaw, radius 0.35 m and cylinder
offset 0.18 m. The score is extra edge margin beyond that envelope, capped at
the 0.15 m preference target. It is an offline body geometry measurement,
not selected-support admission or evidence of actual foot contacts.

For the equally observed **[45,46.686) s prefix**, each run has 17 body samples:

| Metric | v219 | v230 / v231 |
|---|---:|---:|
| Minimum extra edge margin | +0.054742 m | +0.150000 m (capped) |
| Fifth percentile | +0.057507 m | +0.150000 m (capped) |
| Samples at target | 4/17 | 17/17 |
| Completed/successful local rounds | 7/6 | 42/42, plus 1 incomplete start |

Across v219's complete 45–55 s window, minimum extra margin is -0.023160 m,
with 18/100 samples negative. The new recording's whole-window samples all
reach the target, but 80/100 are after the failure; these standing samples
cannot demonstrate improved route execution. The new spatial stair region
contains only 21 samples before the final reactive observation and 5530 after
47 s. All comparisons are descriptive single-run observations; they do not
isolate the effect of shared scoring, height alignment or feedback.
The spatial box is x=[6.7,8.8], y=[-4.8,-2.8], z=[1.3,2.3] m.
See [fair prefix](results/common_active_prefix.json) and
[margin distributions with failure split](results/body_edge_margin_comparison.json).

## Runtime binding and limits

The 12 s actual-graph preflight passed before physics. Post-run SHA checks
preserve all 314 composed source files, 604 installed files and 11 frozen v231
execution files. All 14 native package prefixes were checked. The existing
nine-package/154-distinct-case v230 test receipt was used; no claim of newly
running those component tests is made here.

The original start/yaw/goal, v216 locomotion, stateless-h10 RL policy and
factory-PD startup remain unchanged. Policy SHA-256 is
`7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b`.
Original radius/support guard 0.35 m, offset 0.18 m and vertical inflation
0.55/0.35 m remain unchanged. Actual runtime PCT reference height is **0.30 m**,
matching the original generated v219 profile; earlier offline admission
fixtures used 0.35 m reference height. These are different parameters.
The original freshness, terminal, speed and retry gates remain unchanged.
There is no archived seed, so this is not a same-seed claim. See
[generated configuration gate](results/execution_receipts/configuration_gate.json)
and [post-run source parity](results/execution_receipts/post_run_source_parity.json).
The actual closed capture's native/PCT/controller parameters were separately
checked against that original-profile receipt and match; see
[actual captured profile parity](results/actual_profile_equivalence.json).

Only one global route was recorded in the new run (seven in v219). Two initial
PCT attempts reported static evidence unavailable before the route was
delivered. There are no witness-count-change INFO messages. This does not
prove LIVE queries were absent, but there is no physical witness/detour
evidence establishing that blocked feedback helped this run. GPMP first-round
admission remains a component result, not independently measured per physical
global call here. See [PCT runtime context](results/pct_runtime_context.txt).

## Failure investigation boundary

Read-only source inspection found a possible escaping-exception path: rebound
constraint failure returns false, but the cost callback can continue into
environmental scoring; a nonfinite native motion heading can cause
`EnvironmentalField::assess` to throw. The callback chain has no local catch.
This is a candidate, **not the confirmed crash cause**: no core stack or actual
throw-site evidence was captured. The logged A* failure itself should return
ordinary optimizer failure. Investigate exception propagation and failure
notification before another full-route attempt; do not turn unknown occupancy
verdict 6 into a permanent feedback obstacle to bypass this failure.

## Retention and reproduction

Bulk remains on gpu5070ti at
`/data/sun/vla_mppi_20261009/trials/v231_linux_full_attempt01/`.
The raw archive is 1603415437 bytes with 5896 individually SHA-verified members;
archive SHA-256 is
`aeeee2c941f473845a7a50f752cb748d7bd0f02f974eddafb767dced0c813da5`.
No raw archive, dense capture or CMake build tree is returned locally.

After capture closeout, run `postprocess.py`, `diagnostic_metrics.py`,
`run_margin.py`, `finish_evidence.py`, `render_run.py`, then `compare_video_v2.py`
with the pinned Newton worker interpreter. `render_run.py` is a one-time
output-directory creator and does not rerun physics. Its frozen display input
hashes, adapted executed scripts and per-frame indices are retained remotely.
The inherited 10 overlay and 4 timeline unit tests pass. Videos retain original
pauses. Side-by-side comparison uses the latest actual frame no later than
the common physics time and black after an input recording ends.
The initial comparison encoder could not import imageio and produced no video;
its log/source are preserved. The v2 encoder uses existing FFmpeg pipes and
requires no dependency installation or additional physical run.
Source decoder `Broken pipe` messages occur when closing a pipe after the
needed frames; the v2 comparison process exits zero and each encoded output
passes complete decoding and exact frame-count checks.

## Delivered review videos

| Local regular file | Stream | Frames | Bytes |
|---|---|---:|---:|
| [45–55 s physical-time comparison](delivered/stairs_physics_45_55.mp4) | 2560x764, 30 FPS | 301 | 1796833 |
| [Entire physical-time comparison](delivered/full_physics_comparison.mp4) | 1280x404, 30 FPS | 18017 | 12525260 |
| [Entire new failed attempt](delivered/v230_full_attempt01.mp4) | 1280x720, 30 FPS | 18009 | 15216290 |

All three pass full remote decoding and local-return SHA-256 equality. The
18009 master frames pass causal state/curve checks; all original initial/final
states and pauses are retained. Side-by-side frame mappings are saved in the
two comparison verification JSONs. The 45/48/55 s comparison PNGs and an
additional 300 s master frame were visually inspected: robot, stairs, route,
active/no-active-curve labels and persistent crash label are visible. The long
inherited source header/footer text clips at the side edge; the comparison's
separate physical-time header is fully visible. This display limitation does
not change state selection or acceptance. See [delivery hashes and remote
display provenance](results/delivery_manifest.json).

The accepted physical source/display pair remains **v219/v220**. v230 is still
component-validated, with this failed closed-loop attempt recorded separately.
