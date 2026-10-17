# v189: retain global-route heading at a stopped local corner stub

Stage: experiment + analysis. Status: Mac component and graph checks executed; freeze and full-route
trial authorized, physical outcome recorded separately in RESULTS.md. Version parent: v188. Native source baseline and binary underlay:
v177, whose 649 native source hashes are identical to v188. The Mac binary
underlay is the archived ARM64 v176 workspace; its 649 source hashes were
verified equal to the same parent inventory.

## Behavior and boundary

Truth #2: a shortened local B-spline can end with zero remaining XY displacement
and zero terminal XY velocity. The tracker then uses the body heading and
clears the entire endpoint command, losing the turn toward the global route.

Only when both local heading signals vanish, project the reference position
onto the global route in 3D and advance a 0.5 m carrot using 3D arc length.
Keep zero linear velocity at a captured expired stub, but retain yaw correction
until the existing tracker goal-yaw tolerance. Final-goal capture, reverse
motion, identity, safety, freshness and cancellation retain ownership of their
existing behavior. Standalone tracking defaults to disabled for v82 parity;
the generated Lite3 profile explicitly enables route lookahead.

Validate every route pose before accepting it. A same-owner route refresh
updates tracker path geometry without resetting the initial goal position,
goal yaw or XY latch. The Nav2 same-owner setPlan branch forwards that refresh.

## Source provenance

Before editing, all four source files were checked against the frozen inventory
at `v188/source/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v188/native_sources.json`:

| File under src/ | Copied baseline | Verified baseline SHA-256 |
|---|---|---|
| scan_nav2_controller/include/scan_nav2_controller/tracking_node.hpp | v168/src | b18d8818bc9b71dd6740d9166652fd8ca7f416262191b1bc9d6bdef193e1e93e |
| scan_nav2_controller/src/controller.cpp | v168/src | dcc291f9deb2389214bc50fe62f4c2f5d8ddd52e4bd9716f8e219ccc029d9d39 |
| scan_nav2_controller/test/test_controller.cpp | v168/src | 9eac1727dd1077f158e03778c2b6c972dd0e593e76c639d2fbae091cd4b6de64 |
| lite3_nav2_bridge/lite3_nav2_bridge/profile.py | v176 frozen source snapshot | fe2d0109a6ea8215b98437251dc5e7643f3a3f2c75fad906d39e864ce7beb60b |

The harness comes from the frozen v188 harness snapshot, excluding manifest,
results and nested source snapshots. `native_sources.json` records exactly four
changed native files and overlays their hashes onto the unchanged parent map.
Version references, environment variables and launch checks consistently use
v189; `freeze_host.py` selects v188 as its manifest parent.

## Checks and acceptance

The controller regressions cover disabled defaults, the two yaw-error bands,
alignment completion, same-owner refresh with latch preservation, reverse
motion, final-goal yaw ownership, the 180-degree U-turn and invalid distance
parameters. The standalone probe keeps `V176_TERMINAL_CAPTURE_PASS` and adds
`V189_CORNER_LOOKAHEAD_PASS`, including multi-floor projection, repeated points,
single-vertex/zero-direction fallback, invalid path poses and identity mismatch.
The build script requires both markers and runs the unchanged tracking-parity
test through the controller package's colcon suite.

Run the seven requested Python scripts locally. Record actual outcomes in
`LOCAL_CHECKS.json`; unavailable ROS/native dependencies, sandbox restrictions
and platform skips are not passes. No native GTest, probe or full-route result
is claimed from Python or static checks.

## Authorized Mac execution, 2026-10-13

Dr Sun authorized local Darwin ARM64 verification and one original full-route
trial while an unrelated job holds the gpu5070ti resource gate. The local VLA
repository is the source of truth; no remote experiment or robot actuation is
part of this task. Frozen v177-v188 and the four prepared v189 native files are
preserved. There is no commit.

Restore the eleven verified tarballs from
`gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_20261012/environment/`
into `/private/tmp/vla_stop_audit_20261012`. The installed Docker image is
`sha256:a6326521265b857c85799c5d24eb8d9a78cbb19a25d2b1e5e1d01943cea3524e`.
The compact v176 archive omits inherited metadata/licenses/third-party source;
materialization resolves those only from exact matching hashes in earlier
restored archives. Verify the complete 649-file inventory and v176 binary
receipt, build only `scan_nav2_controller` and `lite3_nav2_bridge`, then verify
the new source/install receipt and installed package prefixes.

Required evidence is 46 unique GTest cases (44 controller, tracking parity,
executor shutdown), two profile tests, both terminal probe markers, Mac host
unit checks, actual loaded-library maps and generated graph parameters. The
checked-in source actually has seven explicit route-heading cases (five
RouteHeadingTest and two PluginTest); record every case from the test XML.
The live profile must retain 2 cm capture and enable the 0.5 m route lookahead.
Clock/applied-state Docker ports follow v189's 24602/24603 service ports.

Both freeze and runtime validate complete quality metadata, including
`native_packages_available == 14`. v184 attempt01 failed at the episode's
package-count check before physics, although its receipt and graph passed.
Preserve that failure. Test the actual v189 receipt gate before freezing,
then freeze source with v188 as the manifest parent and verify it. Full-route
launch checks the receipt again before invoking the original bounded manager.

Run `v189_mac_full_attempt01` with `building_full`, `historical_full`, factory
PD startup, stance hold, 600 s recording cap and the inherited 900 s process
deadline. Preserve actual failure/timeout outcomes. Close original writers
before retention, then audit original-route arrival, final hold, copyback and
recorded replacement-owner stop proofs. One trial is not repeated reliability
or sustained 30 Hz acceptance.

Bulk build/runtime/capture bytes live under the temporary Mac root for this
explicit local exception. Keep compact verification/results/provenance in v189
(expected below 5 MiB excluding inherited source snapshots). Archive closed
raw evidence under `/data/sun/vla_mppi_20261009/mac_archive_v189_20261013/`
on gpu5070ti with byte verification and a local retrieval record; this is file
storage only and does not start a remote GPU workload. Preserve local originals
until durable copy verification. Report any incomplete archive honestly.
