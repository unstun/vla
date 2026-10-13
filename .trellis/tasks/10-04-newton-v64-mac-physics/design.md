# Mac launch boundary

The 2026-10-05 authorized repair extension is designed in the Newton experiment's
`audits/2026-10-05_safe_mapping_repair/PLAN.md`: producer-level compact history,
equivalent native loops, single-writer immutable snapshot publication, then
conservative reduction of complete accumulated LiDAR frames. Preserve the older
v64 launch design below as historical context; new versions own all new bytes.

v64 is an integration/host launch package: native parent v63 (exact source), runtime parent v59 (exact Newton/graph/backend behavior except declared host paths and run identity). The gap is that v63 owns no physical entry point or retained installed binaries. Build v63 inside a uniquely owned cached ROS container, retain that container only for the trial and verify source/install hashes at entry. Use the existing Mac Newton environment and original ARM64 factory process. Regenerate the exact pinned physical-floor payload from existing verified maps into temporary storage and require its original SHA-256. Native configuration, navigation contract, controller, policy, geometry, planner and stopping remain unchanged.

The launch gate explicitly requires the available Mac/recorded native suites and immutable v63 source/build receipts. It does not relabel missing original remote-corner qualification as passed: this user-authorized run is bounded experimental validation, not a promotion of v63 or the v48 reference. Complete live occupancy/support/PVA/dynamics/freshness/backend stop gates stay active. Full qualification remains independently pending. No v49 deadline. Only new v64 launch/gate/generator/analysis code and copied runtime entry files are owned; frozen v59/v62/v63 cannot be edited.

Raw run and build data go in a unique /private/tmp/vla_newton_v64_* root, mounted into the owned container. Reuse the managed supervisor/retention through an explicit temporary root. Keep archived raw evidence at that bounded location, hashes/locator locally, and remove owned containers on every exit. No GPU calls, heavy downloads, permanent build tree or PNG sequence. Declare the temporary local-storage exception inherent in Dr Sun's Mac execution instruction.
