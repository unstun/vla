# v196 Mac attempt 01: full-route gate passed

Stage: experiment + analysis. This is a new execution after the reboot erased the previous temporary capture. The earlier reported arrival is not recoverable trial evidence and is not combined with this run. Frozen v196 source, configuration and historical qualification files remain unchanged.

The new capture reports **FINISHED**, route_arrived=True, full_route_gate_passed=True, final_pd_hold=True. This is one Mac ARM64 CPU Newton / ARM64 Foxy trial, not repeated reliability, sustained 30 Hz, general collision-clearance or real-robot acceptance.

## v194 versus v196

| Measurement | v194 | v196 |
|---|---:|---:|
| terminal_status | FINISHED | FINISHED |
| route_arrived | true | true |
| full_route_gate_passed | true | true |
| final_pd_hold | true | true |
| final_xy_error_m | 0.121167851 | 0.132456307 |
| final_height_error_m | 0.006756115 | 0.006161976 |
| final_yaw_error_rad | 0.104157523 | 0.157312296 |
| navigation_sim_s | 126.507451057 | 115.561238289 |
| navigation_wall_s | 126.540359958 | 118.348343542 |
| actual_rtf | 0.999739934 | 0.976449985 |
| local_planning_successful_wall_hz | 23.676240537 | 24.630678493 |
| controller_wall_hz | 29.811494710 | 29.935137379 |
| pct_route_publications | 3 | 102 |
| longest_pause_sim_s | 10.194396973 | 4.797363281 |
| emergency_stop_entries | 9 | 12 |
| emergency_stop_exits | 9 | 12 |
| direct_command_stop_count | 17 | 9 |
| direct_command_zero_wall_s | 9.422262201 | 3.276432741 |
| completed_wait_recoveries | 1 | 0 |
| native_trajectory_timeouts | 0 | 0 |
| PCT refresh_status | N/A (not recorded) | terminal_approach |
| PCT retained_count | N/A (not recorded) | 3 |

Both use direct Nav2 Twist. Rates are wall-clock measurements from the frozen analyzer; simulation/wall time excludes startup and closure. Final height error is relative to original goal ground Z + 0.30 m. The exact final PD state and unchanged goal pose are recorded in trial_analysis.json. Broader v189/v192 comparisons and source hashes are in comparison.json; v192 did not finish and v189 used a different command/recovery path.

## Retained Mac cohorts

| Measurement | v189 | v192 | v194 | v196 |
|---|---:|---:|---:|---:|
| terminal_status | FINISHED | FAILED | FINISHED | FINISHED |
| route_arrived | true | false | true | true |
| full_route_gate_passed | false | false | true | true |
| final_xy_error_m | 0.138237115 | 4.832351783 | 0.121167851 | 0.132456307 |
| final_height_error_m | 0.015110302 | 0.008518028 | 0.006756115 | 0.006161976 |
| final_yaw_error_rad | 0.377481246 | 0.525199548 | 0.104157523 | 0.157312296 |
| navigation_sim_s | 176.660038948 | 107.865468025 | 126.507451057 | 115.561238289 |
| navigation_wall_s | 212.748508333 | 117.584897625 | 126.540359958 | 118.348343542 |
| actual_rtf | 0.830370282 | 0.917341174 | 0.999739934 | 0.976449985 |
| local_planning_successful_wall_hz | 17.946071772 | 26.066272641 | 23.676240537 | 24.630678493 |
| controller_wall_hz | 24.562429855 | 29.984195176 | 29.811494710 | 29.935137379 |

## Pauses and PCT refresh

- 112.369873–114.068939 s: 1.699066 simulation seconds / 1.525213 wall seconds; mean XYZ [3.5144552654690213, -0.5496002303229438, 4.821797927220662].
- 121.764709–126.562073 s: 4.797363 simulation seconds / 5.680072 wall seconds; mean XYZ [2.0698216545338535, -2.9201327878601697, 4.827232711169184].

The old v194 stall lasted 10.194397 s. v196 visited its 1 m neighborhood: True. Its longest >=1 s low-speed interval in that neighborhood was 0.000000 s; a >=10 s stall was observed: False. These are spatially compared single captures, not evidence that all future stalls are eliminated. Terminal holding is included in the general pause list.

The configured PCT refresh is 1 Hz. Actual ROS route publications are 102; final refresh_status=terminal_approach, retained_count=3. HTTP status samples and status transitions are reported separately and cannot count every planning invocation. v194 did not export these two counters; unavailable is not zero.

Emergency entries/exits, zero commands and completed Nav2 Wait recoveries are different measurements. Option B has no P2B measured-stop proof. A zero command alone does not establish physical stillness. The final PD hold is checked independently by the original full-route verifier.

## Artifacts and reproducibility

See ARTIFACTS.json, trial_archive_manifest.json and remote_verification.json for the remotely verified closed trial. The rebuilt native overlay and fresh component-test evidence have separate archive identities. Heavy captures remain in the task's temporary Mac workspace and durable gpu5070ti archive. The v197 display, if the route gate passes, replays this capture with zero physics steps.
