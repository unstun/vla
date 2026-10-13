# v67 actual Newton Mac trial

The repaired native v63 runs in actual Newton on Mac. Trial01 climbs the first stairs but original heartbeat_stale stopping ends it at31.614254 native seconds, before the90s endpoint. Native round max494.716ms; full frequency/clock-corrected metrics are in audits/2026-10-04_mac_newton/trial01. No90s, late-corner or30Hz pass is claimed. State copyback passes.

The owned runtime container retained ROS-run descendants after the graph launcher exited, so closed-log retention correctly refused an open scan.log. The orchestrator then removed the container. A separately recorded closed-retention retry verifies no writers and losslessly archives original bytes outside repo. The failure and process exit2 remain preserved. v68 restores full runtime-container teardown before retention while keeping a bounded installed-byte workspace available for another independent trial. Native/physics/control/safety are unchanged.
