# v193: full display review of v192_mac_full_attempt01

Stage: experiment + analysis. Authorized display-only version; physical parent
`v192`, display parent `v190`, native implementation `v191`. Skip Trellis for
this session. Preserve frozen v189, v190, v191, v192, recovery_v176,
recovery_v189, recovery_v191 and every original recording byte.

Replay physical frame 0, all recorded factory PD startup, and the complete run
through its last state at 118.88629150390625 s physics. The source travelled
72.57228851559466 m and ended FAILED/nav2_failed, without arrival or full-route
acceptance. Rendering cannot change that outcome or qualify navigation.

Follow v190's Mac ARM64 Cocoa invisible ViewerGL, CPU model construction and
recorded-pose replay with zero physics steps. Startup uses recorded simulation
timestamps; navigation uses original wall timestamps at 1:1. Use causal
zero-order sampling at 30 fps, without pose interpolation, stitching, resets,
removed pauses or speedup. Extend the terminal sampling grid by at most one
frame to include the exact final source state, which v190's floor grid could omit.

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

Run test_overlay.py (10 cases), test_timeline.py (4 cases), prepare_mac.py,
render_capture.py and verify_video.py using the existing Newton Mac interpreter.
Validate every frame index, endpoint coverage, curve/route/solve causality,
full video decoding and decoded start/startup/middle/corner/end images. Return
compact provenance under returned/ and inspect before freezing. Deliver a
regular MP4 at delivered/v192_mac_full_attempt01.mp4. Archive the MP4 and compact
v193 source/provenance to gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v192_20261014/
and compare SHA-256. Update only the version index/current state after delivery.

Regeneration: use the existing
`.pipeline/experiments/2026-09-26_newton_macos_policy/runtime/.venv/bin/python`
with `PYTHONDONTWRITEBYTECODE=1` to run `versions/v193/run_mac.py`. The original
run lives at `/private/tmp/vla_stop_audit_20261012/v192_mac_full_attempt01/runs/v192_mac_full_attempt01`
and its durable source archive is recorded by v192's trial_archive_manifest.json
and remote_verification.json. The temporary video_v193 execution folder must be
absent before a fresh run; retain prior execution outputs under a new name.
