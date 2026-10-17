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

## Recovery and preserved identity

All 11 environment archives passed the hashes in frozen v196/verification/environment_archives.json. The ARM64 Foxy rebuild passed 93 colcon entries, zero errors/failures/skips, generated profiles and both terminal probes. The first launch was rejected before physics because a fresh test receipt differs from the frozen receipt. Its failed preflight and fresh rebuild evidence were preserved. Restoring the original formatting of semantically identical source_identity.json made all 3,650 pinned source/install file hashes match. The pinned receipt then passed the original runtime gate. No frozen v196 code, configuration, manifest, quality or verification file was changed.

## Verified archives

- Trial: gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v196_20261014/v196_mac_full_attempt01.tar
- Trial bytes: 416542720; SHA-256: `dc3b8620a8e2fb0fb2b04da371c64ac7465ede955492154fdbc1505433610a8d`.
- Remote verification: 287 files, one symlink and all 1,160 raw ZIP members.
- Native overlay: recovery_v196.tar in the same directory; SHA-256 `6dc4d96063d9d0d5bf452ea6d3e7e3da1d59a7838ace294264aed5eca9df844d`.
- Restoration/build/preflight evidence: resume_evidence.tar in the same directory.
- Frozen display source/provenance: v197_source_provenance.tar.gz; SHA-256 `05b75e5ff0243bb3b1b2f96c8cb8ed66b4ff22784f11c4d92bed6a069c9a9869`.
- Local compact provenance: /Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v196/results/v196_mac_full_attempt01/ARTIFACTS.json.

## Completed v197 video

Video: [.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v197/delivered/v196_mac_full_attempt01.mp4](/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v197/delivered/v196_mac_full_attempt01.mp4)

The regular MP4 is 12028789 bytes, 3880 frames, 1280x720, 30 FPS and 129.333333333 seconds. SHA-256: `7e063950f0a8974ddc4f49007ba17a307aeb86c9bd5ff2f4a97fe7e717b74f53`. The remote MP4 at gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v196_20261014/v196_mac_full_attempt01.mp4 has identical bytes. Startup begins at actual zero physics steps; navigation uses original wall time at 1:1; all pauses and the final PD hold are retained. All 14 unit tests, causal timeline/curve checks, full decoding and nine manually inspected decoded samples passed. The final frame says `arrived (nav2_arrived)` and shows no expired cyan spline. Rendering executed zero physics steps.

Visual QA: /Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v197/VISUAL_QA.md

Contact sheet: /Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v197/returned/visual_qa/contact_sheet.jpg

Frozen v196 verification passed after execution and rendering: 5,019 source pairs and 618 runtime inputs. v197 freeze and verify passed with 5033 source pairs. The version index now points to v197 display and v196 as the latest physical trial. The result remains one declared simulator trial, not repeated reliability or real-robot validation.
