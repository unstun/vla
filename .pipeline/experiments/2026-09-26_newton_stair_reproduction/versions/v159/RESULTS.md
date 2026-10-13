# v159 results

Future TF pose versus ROS clock ordering: parent regression fails, candidate
passes36unique controller test cases (39colcon entries including wrappers).
Actual loaded controller library verified; v158planner underlay unchanged.
18host tests pass. Source frozen3603pairs and618runtime inputs.

Full local trial01 is FAILED, not accepted arrival.77.077948m,136.380203native
seconds,RTF0.994077, no fall; six mid-route revocations were followed by resumed
motion. Neither v158steering prefix nor v159future-pose fallback triggered.
At126.052353s, requested_goal_reached cancels generation7. By first measured
stop proof127.146751404s, yaw drifts beyond configured0.25rad.288measured
stop proofs arrive, so missing stop evidence is ruled out. At135s yaw error
is0.439448rad. The stopped owner cannot correct it, and FollowPath aborts on
progress timeout. Final action FAILED is preserved.

All291trial files remotely archived and verified:453775360bytes, SHA256
031cb841bd57191f7f3dce1ac55c2b8be4b89155b7a57c697953c949fbef7ac1.
See results/v159_mac_full_attempt01/archive_receipt.json and metrics.json.
Mac results do not establish Linux reliability. v160tightens entry into goal
hold while preserving existing final acceptance and stop proof.
