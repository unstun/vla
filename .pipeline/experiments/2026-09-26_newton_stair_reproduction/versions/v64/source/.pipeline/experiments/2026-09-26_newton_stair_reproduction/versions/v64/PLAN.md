# Newton validation on Mac

Stage: experiment + analysis. Dr Sun explicitly authorized testing Newton on Mac while gpu5070ti is busy. Run the repaired native planner with original Building geometry, original historical route, actual sensors, original locomotion/factory startup and unchanged stop/safety rules. Measure physical progress/pauses, per-round solve latency, successful local Hz and actual simulation/wall clocks. Keep frozen predecessors immutable and preserve failed trials. Keep raw captures and temporary build/install products outside the repository; return compact provenance/report/plot and an optional review MP4. Mac timing is separate from gpu5070ti timing.

# Mac launch boundary

v64 is an integration/host launch package: native parent v63 (exact source), runtime parent v59 (exact Newton/graph/backend behavior except declared host paths and run identity). The gap is that v63 owns no physical entry point or retained installed binaries. Build v63 inside a uniquely owned cached ROS container, retain that container only for the trial and verify source/install hashes at entry. Use the existing Mac Newton environment and original ARM64 factory process. Regenerate the exact pinned physical-floor payload from existing verified maps into temporary storage and require its original SHA-256. Native configuration, navigation contract, controller, policy, geometry, planner and stopping remain unchanged.

The launch gate explicitly requires the available Mac/recorded native suites and immutable v63 source/build receipts. It does not relabel missing original remote-corner qualification as passed: this user-authorized run is bounded experimental validation, not a promotion of v63 or the v48 reference. Complete live occupancy/support/PVA/dynamics/freshness/backend stop gates stay active. Full qualification remains independently pending. No v49 deadline. Only new v64 launch/gate/generator/analysis code and copied runtime entry files are owned; frozen v59/v62/v63 cannot be edited.

Raw run and build data go in a unique /private/tmp/vla_newton_v64_* root, mounted into the owned container. Reuse the managed supervisor/retention through an explicit temporary root. Keep archived raw evidence at that bounded location, hashes/locator locally, and remove owned containers on every exit. No GPU calls, heavy downloads, permanent build tree or PNG sequence. Declare the temporary local-storage exception inherent in Dr Sun's Mac execution instruction.

# Execute

1. Verify local Python/Newton/IPC/factory and all source/geometry/policy/map identities.
2. Copy the minimum v59 runtime files into v64, reference unchanged dependencies; add explicit host build/entry/storage scope and negative source/build gate tests.
3. Build exact v63 in the cached local ROS image; return hashes and qualify installed bytes. Derive/hash the physical input in temporary storage.
4. Freeze the v64 source/config/host launch identity without a physics-success claim; execute a bounded 90-second actual Newton Building trial, repeating the independently initialized trial if the full duration and host setup pass.
5. Analyze original captures and produce compact metrics/time-series/report, bind results to version/host/clocks and preserve failures. Recheck cleanup/source hashes. Update task/spec state; no automatic commit or broad staging.
