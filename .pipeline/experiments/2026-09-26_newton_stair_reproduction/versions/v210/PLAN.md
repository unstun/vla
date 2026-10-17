# v210: full navigation with the frozen v208 locomotion adapter

One user-authorized original-start historical_full Building trial on gpu5070ti.
The sole behavioral difference from v206 is selecting v208 NewtonStance before
constructing the robot. Preserve v206 native binaries, PCT/SCAN, Tracker, 1 Hz
refresh, ordinary retries, non-retry stand timeout, all endpoint tolerances,
factory startup, V12 policy, exact geometry, sensors and solver settings.

Owned files: the launch binding, an explicit physics-process entry wrapper,
source provenance, integration preflight, and post-run analysis/video bindings.
No frozen parent files change. No local compilation or simulation. Reuse the
previously built 14-package v206 install after source/binary hash checks.

The local VLA repository is authoritative. Sync only owned source to its existing
gpu5070ti execution copy. Verify parent manifests, the prior complete sync
inventory, native install receipt and new source hashes before physics. The
preflight constructs the actual graph-enabled CPU robot with v208 but takes no
physics steps. The full trial starts from the original factory crouch, not a
saved terminal pose. One moving attempt; retain any failure without retuning.

The unchanged v196 full-route verifier is rebound only to the v210 integration
identity. Success requires original-start continuous physics, native arrival,
original position/height/yaw tolerance, no fall and measured final fixed-PD hold.
The driver retains its two-second final hold. Record ownership, gains, forces,
body motion, source identity and the exact terminal outcome separately.

Keep raw logs/clouds on gpu5070ti in a verified closed archive. Return compact
results and a regular MP4 showing startup, the full route, pauses and terminal
state. The render must use only the recorded states, with zero new physics.
