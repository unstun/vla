---
origin: ai+web
reviewed: false
date: 2026-09-21
status: surveyed
claim_boundary: "Forum/docs/discussion snippets. Not executed. NVIDIA RTX has no stock MID-360 config in the inspected docs."
---

# Isaac Sim RTX, forums, and anti-patterns

## NVIDIA RTX LiDAR (do not switch the Building runner onto this)

Official docs (Isaac Sim “latest” and 5.0): RTX lidars are `OmniLidar`
prims / `IsaacSensorCreateRtxLidar` / `LidarRtx`, with a named
`config`/`variant` library (`SUPPORTED_LIDAR_CONFIGS`). Setting
`config=None` plus `OmniSensorGenericLidarCoreEmitterStateAPI:s00N:*`
builds a custom emitter table.

https://docs.isaacsim.omniverse.nvidia.com/latest/sensors/isaacsim_sensors_rtx_lidar.html

Inspected docs do **not** list a Livox MID-360 stock config.

[Isaac Sim discussion #685](https://github.com/isaac-sim/IsaacSim/discussions/685):
staff path for non-repetitive Livox is `emitterStateArrays` filled from
**recorded** azimuth/elevation/fireTimeNs/channelId, `stateResolutionStep=1`,
cycle length = observed repeat period. Alternative mentioned: PhysX lidar
fed from a real Mid-360 recording. That is a different stack from Lab
`MultiMeshRayCaster`.

[NVIDIA forum 283074](https://forums.developer.nvidia.com/t/livox-mid360/283074):
a user “MID-360” snippet starts from Ouster `config="OS1"` and a **40-emitter
rotary** elevation list from −7° to ~50.5°, `scanType: ROTARY`,
`farRangeM: 40`. That is a homemade spinning lidar with MID-360-like
vertical span, **not** `mid360.csv`.

## Gazebo `gpu_lidar` rings (anti-pattern)

[LXRobotics note](https://lxrobotics.com/blog/livox-mid-360-gazebo)
attaches Gazebo `gpu_lidar` at 10 Hz, 720×40, 0.01–40 m, VFOV 0–0.9774 rad.
That is a dense spinning model. The author states the real MID-360 is
non-repetitive. Do not copy this as “MID-360 matching.”

## Real-robot contract (not a sim)

Seeed’s MID-360 ROS wiki (lead): `livox_ros_driver2` launch
`msg_MID360.launch` / `rviz_MID360.launch`.
Already-surveyed EMOS Lite3 plugin (`2026-09-16` notes) expects
`PointCloud2` on `/livox/lidar` plus `/livox/imu`.
That is the physical topic shape. No bag-vs-sim comparison exists in
this repository.
---
