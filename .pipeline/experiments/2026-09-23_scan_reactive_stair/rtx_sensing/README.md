# RTX animated-human sensing gate

Stage: experiment and analysis. Dr Sun authorized continuing the stair/person
integration and requested an actual local video on 2026-09-25 (Pacific time).

The immediate gap is that the existing Warp sensor caches unskinned mesh
vertices. This package tests the installed Isaac Sim 5.1 RTX sensor against the
same pinned official police USD and official retarget cache, before changing
the Building runner. Local VLA files are the source of truth; gpu5070ti is an
execution copy. Existing accepted runs and frozen planner thresholds stay intact.

Execution order:

1. Run the imported RTX module lifecycle probe with a 150-second wall limit.
   Require a natural zero exit and the `teardown_completed` marker.
2. Hold the human root and sensor fixed. Compare official walk frames 0 and 22,
   repeat frame 0 as a control, and retain raw RTX returns and rendered images.
   Require at least 30 human-surface points per capture; the symmetric nearest
   point distance between different poses must exceed both 0.01 m and three
   times the repeated-pose control. Record these diagnostic thresholds before
   execution. Rendered geometry must visibly change too.
3. Only after sensing passes, prepare a separated Building encounter and the
   live SCAN/PCT/tracker process graph. Retain collision/fall/outcome/timing
   evidence and return a playable video. A sensing video alone is not A4.

The first implementation changes only this new `rtx_sensing/` package and the
current task records. No baseline refactor or sensor substitution in existing
runs is involved. `Example_Rotary` answers the skin-geometry question only; it
does not establish MID-360 parity. Any later runtime sensor change requires its
own recorded input contract and tests.

The executor creates a fresh remote directory, verifies all staged SHA-256
values before and after execution, limits the child process with GNU timeout,
returns all outputs, and compares remote/local artifact hashes. It records
timeouts and GPU processes after execution rather than treating result-file
existence as success.

Primary references:
- [Isaac Sim 5.1 RTX LiDAR](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/sensors/isaacsim_sensors_rtx_lidar.html)
- The installed `isaacsim.sensors.rtx/impl/lidar_rtx.py` (source identity recorded
  in each probe), and `../isaac_candidate/ANIMATED_MESH_LIDAR_AUDIT.md`.

## Follow-up geometric interface gate (declared before execution)

`rtx_mid360.py` authors an opt-in RTX geometric sensor from the pinned Livox
CSV. It emits the existing 20,000 ordered directions in each 0.1-second window,
with 0.1–40 m range and one sensor pose for the entire sweep. It does not claim
a manufacturer-calibrated RTX profile. The original CSV loader is reused.

`probe_mid360_geometry.py` first places the sensor at the center of a 12 m cube
and compares actual returns to analytic ray/box intersections for two different
CSV windows. Both must return 20,000 points with maximum bidirectional nearest
point error below 0.005 m. Then it removes the cube and moves the official actor
at 0.3 m/s for 40 frames, recording RGB, actual point clouds, and unchanged
`scan_10` core results. At least 25 frames must contain one confirmed track with
one persistent identity. Flat support is an explicitly synthetic fixture;
actor truth is used only for scoring. This is not a Building or ROS result.
Every moving-frame return must match a direction in that same requested CSV
window within 0.0001 unit-vector distance; a stale render window makes the
tracker input incomplete and fails this gate.

## Shutdown diagnosis and operational choice

The original import probe hid a `ModuleNotFoundError`: RTX was not enabled in
IsaacLab's experience, and the default fast shutdown exited before the error
propagated. Explicit extension enablement plus full cleanup passed the isolated
import lifecycle in `import_v3_enabled`.

The full sensor scene exposed two separate shutdown failures. The pinned
`SimulationContext` STOP callback renders until PLAY resumes; disabling this
interactive callback for terminal shutdown removed the hang. Full extension
cleanup then returned to Python but the interpreter exited with SIGSEGV, also
after scene-local objects were released (`sensing_v3_stop_callback` and
`sensing_v4_object_lifetime`). These failed executions remain failures.

Subsequent sensor probes explicitly release the timeline, callbacks, annotators,
render products and scene objects, then use Isaac Sim's documented default
`fast_shutdown=True`. The child writes `resources_released_close_requested`
before this process-exiting API; the parent requires a zero exit, GPU release,
and matching returned artifacts. It reports `teardown_pass: false` and
`process_release_pass` separately. This does not claim full extension teardown,
and does not change the frozen geometric/shape acceptance thresholds.
