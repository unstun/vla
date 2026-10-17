# Building stair pedestrian episode: launcher blocked at actor intake

Stage: experiment and analysis. Status: source audit only. No Isaac episode,
actuation, remote command, or new launch overlay was run or prepared.

## Reproducible local findings

1. The current P2B launcher invokes `lite3_sim_bridge.run_pct_scan_building`
   (`isaac_runner/run_two_goal_pilot.py:1442`) and its frozen `pilot.json` has
   two same-height goals on the flat platform (`z=1.5608844757080078 m`). It
   starts the socket PCT worker and SCAN/controller, but no PCT topic sidecar
   or moving-cluster tracker (`run_two_goal_pilot.py:1451-1504`). An isolated
   future launcher could add those three ROS processes in one domain.
2. The Building runner parser has no human/person/pedestrian/actor option. A
   direct, ROS-free import of `build_parser()` returned
   `human_actor_options: []`. The runner configures the navigation LiDAR with
   only `/World/ground` and its terrain target
   (`run_pct_scan_building.py:421-431`). Thus a visible person object alone
   would not establish LiDAR observation or sensor-derived tracking.
3. The pinned bridge contains an official Isaac human URL and a separate
   forest/Office implementation with a kinematic actor and dynamic raycast
   targets (`official_human_contract.py:7-15`,
   `run_isaac_v12_fallback.py:2050-2110,2140-2171,4306-4430`). That
   implementation is not wired into the Building runner. A local file search
   under the pinned bridge and pilot asset directory found no official human
   USD or Biped retarget cache to verify. The source code is reusable evidence
   for a future Building port, not a verified Building actor asset.

Source SHA-256 at this audit:

| File | SHA-256 |
| --- | --- |
| `isaac_runner/run_two_goal_pilot.py` | `be2291da53a61fefe8a51d8cdc4fb43a7c089a047677e7ede63976637257f1da` |
| pinned bridge `run_pct_scan_building.py` | `1490dc85146ce7ea71f05c4f5520639da1a342a13e9dfcd8ce0ba04f21c8a76b` |
| pinned bridge `run_isaac_v12_fallback.py` | `6104fe686bcd3bc0480c0afc1b41dde84d1a35d45a6dbbe9e51d98e6719ba3e3` |
| pinned bridge `official_human_contract.py` | `a23020f3f269a044bf3ea0b65830309de155c07b19419f9ab52b1df5cd1621ff` |
| `p2b_execution/inputs/pilot.json` | `623db10bb5c500c9afc033cbfab25097c6aa75e0245c9b85cbb6582833c9c8ed` |

## Required next implementation gate

An isolated, hash-gated Building runner overlay must first place a labelled
human actor on a geometry-checked stair route, update its physical pose in
simulation time, and register its moving mesh with the navigation LiDAR using
`track_mesh_transforms=True`. The official asset/cache, if used, needs an
identity check in the Isaac environment. Simulator actor truth must be logged
only for scoring; it must not publish the current-person snapshot. The ROS
launcher then needs to start built `scan_09`, the clock-gated terrain sidecar,
and the LiDAR tracker on the same `/clock`/ROS domain and record the source
and install hashes before and after the episode.

Until those gates are implemented and checked, a moving box, rendered-only
human, or synthetic tracked-person publisher cannot stand in for the requested
sensor-derived pedestrian stair trial. No execution or integration claim is
made from this audit.
