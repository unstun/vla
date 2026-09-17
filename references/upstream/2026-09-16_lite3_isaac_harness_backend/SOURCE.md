# Lite3 Isaac Navigation Sources And Qualification

This acquisition reuses existing code without modifying either sibling project.
It does not establish a complete HarnessVLN integration or a new physical run.

## Committed bridge

The 79-file integration/lite3_sim_bridge tree is exported from machine-dog-nav
848b4aecd01237805e0564c88d3ba09146fd2353 on codex/scan-foxy-isaac. The sibling's
bridge subtree matched that commit when inspected. The unrelated dirty tree
was not copied. acquisition.json records commit/tree identity and every hash.

Recreate with export_bridge.py. It reads git objects, refuses to overwrite a
changed reference, and never resets or edits the source checkout.

## Native PCT/SCAN

Canonical repository: https://github.com/yagami-light7/PCT-SCAN-ROS2.
Commit: 1cf45a1c12ca785ce533293302be09d51daf0ccb.

- source/pct_scan_base: 65 selected canonical planner/notice files, mapped to
  the six-package ROS workspace layout, read from committed git objects.
- source/pct_scan_foxy: the same files with eight explicit recorded adaptations.
- source/pct_global: 145 committed global PCT source and mixed-license notice
  files. No planner binaries, map or scene are represented as newly built.

native_planner_manifest.original.json preserves the inspected sibling import
manifest. Foxy header and callback compatibility, existing dependency exports
and the Lite3 body-to-world odometry velocity representation are the declared
adaptations. The exact source line edits, including original line endings, are
stored in foxy_adaptations.json. All base and resulting hashes were checked
against the source manifest before export. No optimizer edits were introduced.

freeze_native_planner.py obtains the canonical blobs from the existing clean
upstream checkout and records the adaptations. To verify or recreate the port
without reading either sibling repository, run:

    python3 references/upstream/2026-09-16_lite3_isaac_harness_backend/rebuild_frozen_port.py

The base blobs are regenerable from the public pinned commit using the path
mapping in native_planner_manifest.original.json. The resulting port is
regenerable from those blobs plus the tracked line edits. Do not replace the
native port with the historical project-modified SCAN workspace.

Preserve LICENSE, NOTICE, THIRD_PARTY_NOTICES.md, LICENSES and nested PCT
notices. The upstream includes multiple component licenses; this record does
not assign one blanket license to the entire combined project.

## Tests and live runtime resources

Selected local bridge tests: 93 passed, one rclpy-dependent test skipped,
15 subtests passed. Raw output: validation/bridge_tests.log.

The previously skipped dual-cloud ROS test was subsequently executed with the
other transport cases in the existing 5070 Ti Foxy image. Eight transport tests
passed under actual Python 3.8.10/rclpy, with a read-only source mount and
network=none. Raw evidence:
validation/ros_transport_20260916T140123Z/. The source hash gate matched all
79 transferred files and the full image ID is recorded. The upstream test's
unclosed audit-file ResourceWarning and normal socket-reset warning remain
visible in the raw log. No GPU, Isaac process or physical device was used.

qualify_ros_transport.py reproduces this bounded qualification using the
existing Podman image and its own remote path. The inspected host has
/home/sun/miniconda3/envs/isaaclab and the native Building execution/asset
directories. Default PATH checks for docker/ros2 had missed this existing stack.

## Remaining baseline gate

The committed Building runner differs from the native_full02 executed runner;
the other 150 compared execution-source files matched their current sources.
The exact historical runner SHA-256 is
71bf6a12344fd6554f04522533f1842f153ef677c93f9dabd87abfd97640917f.
The selected committed runner SHA-256 is
1490dc85146ce7ea71f05c4f5520639da1a342a13e9dfcd8ce0ba04f21c8a76b.
The task's research/runner_delta.diff and runner_delta_identity.json record
the source comparison: camera intrinsics/pose metadata and capture cadence
changed. No direct planning/control algorithm change was found in that diff,
but changed recording checks and scheduling still need runtime qualification.
Scene/map/configuration/checkpoint freeze and a fresh bounded Isaac run are
required before claiming a new accepted navigation baseline.
The original VLA September 11 snapshots and all historical run evidence remain
unchanged.
