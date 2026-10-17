# v195: full display review of v194_mac_full_attempt01

Stage: experiment + analysis. Authorized display-only version; physical parent
`v194`, display parent `v193`, native implementation `v194`. Execution follows
Dr Sun's explicit scope. No Trellis task is created without separate consent.
Preserve frozen v189, v190, v191, v192, v193 and v194, recovery_v176,
recovery_v189, recovery_v191, recovery_v194, and both complete trial directories
v192_mac_full_attempt01 and v194_mac_full_attempt01. Compare every file hash,
size, mode, modification time, directory entry and symlink before and after.

Replay physical frame 0, all recorded factory PD startup, and the complete run
through its last state at 137.5282745361328 s physics. The source ended FINISHED,
with arrived=true, full_route_verification.passed=true and final_pd_hold=true.
Its sensor-sampled path is 77.03407366997271 m; the complete recorded body path
is 78.15352131927641 m. These are different sampling measures. This display
inherits one physical trial's declared result; it adds no physical acceptance.
The unchanged metrics.json full_qualification=false is retained separately
from outcome.json full_qualification=true and the passed full-route verifier.

Follow v193's Mac ARM64 Cocoa invisible ViewerGL, CPU model construction and
recorded-pose replay with zero physics steps. Startup uses recorded simulation
timestamps; navigation uses original wall timestamps at 1:1. Use causal
zero-order sampling at 30 fps, without pose interpolation, stitching, resets,
removed pauses or speedup. Preserve v193's terminal ceiling grid (at most one
extra frame) to include the exact final source state. Render 1280 x 720 at 30 fps
inside `/private/tmp/vla_stop_audit_20261012/video_v195` only.

Option B's recorded Bspline messages have no P2B identities/admissions. The
latest non-emergency Bspline, keyed by traj_id, becomes active; any emergency
Bspline clears it. Cyan means the latest recorded SCAN spline under a fresh
direct /quad_0/cmd_vel Twist stream, not a controller admission proof. Require
causal wall and simulation clocks, a command at most 150 ms old in both clocks,
and curve phase/event age within the recorded tracking window (150 ms maximum
endpoint grace only for a nonzero command). A fresh zero command may retain a
curve within its active tracking window. After stale commands or emergency
stop, hide cyan until new valid evidence. Orange is the latest causally observed
PCT route (`data.poses`), held until replaced or cleared. Solve timing shows only
the latest completed round, including failures.

The exact final navigation label is `arrived (nav2_arrived)`. The final physical
state is FIXED_STAND, command=[0,0,0], policy_owns_joints=false. The last stored
normal spline is #3005, but its tracking window has expired and the latest direct
zero command is older than 150 ms on both clocks. Assert no visible final cyan
trajectory, without deleting the retained original spline.

Run test_overlay.py (10 cases), test_timeline.py (4 cases), prepare_mac.py,
render_capture.py and verify_video.py using the existing Newton Mac interpreter.
Validate every frame index, endpoint coverage, curve/route/solve causality,
full video decoding and decoded start/startup/middle/corner/end images. Return
compact provenance under returned/ and inspect before freezing. Deliver a
regular MP4 at delivered/v194_mac_full_attempt01.mp4. Archive the MP4 and compact
v195 source/provenance to gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v194_20261014/
and compare SHA-256. Update only the version index/current state after delivery.

Regeneration: use the existing
`.pipeline/experiments/2026-09-26_newton_macos_policy/runtime/.venv/bin/python`
with `PYTHONDONTWRITEBYTECODE=1` to run `versions/v195/run_mac.py`. The original
run lives at `/private/tmp/vla_stop_audit_20261012/v194_mac_full_attempt01/runs/v194_mac_full_attempt01`
and its durable source archive is recorded by v194's trial_archive_manifest.json
and remote_verification.json. The temporary video_v195 execution folder must be
absent before a fresh run; retain prior execution outputs under a new name.

Changes are limited to this version's display files and the requested
versions/README.md and versions/current.json index updates. Keep overlay and
timeline implementations and their 10 + 4 tests byte-identical to v193. Adapt
only run/version identities, exact successful outcome checks and provenance.
Local source of truth is this v195 directory. The render must pass input hashes,
full decode, every-frame causality, visual QA, and local/remote MP4 SHA-256 and
size equality before freeze. Return source/provenance, frame/event metadata,
ten representative decoded samples, a contact sheet, and the regular review MP4
(expected under 80 MB); retain heavy raw inputs and archives on gpu5070ti.
A failed or incomplete render is display evidence only and cannot change v194.

Execution order: snapshot protected paths; check the remote raw archive; adapt
and hash display sources; run run_mac.py with the recorded working interpreter;
inspect decoded samples and write VISUAL_QA.md; archive and verify the regular
MP4; compare protected paths; freeze and verify; archive the frozen display
source/review; update only the version index and current metadata. Never remove
or overwrite earlier execution output or any protected source.
