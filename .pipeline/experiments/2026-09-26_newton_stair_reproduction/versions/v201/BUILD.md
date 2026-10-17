# Rebuild and fixed-input checks

Local sources in this version are authoritative. Use the restored underlay from
v200's BUILD.md; it is mounted read-only. No simulator or full-route launcher is
used by these instructions.

From this version directory:

```bash
python3 materialize_components.py \
  --underlay /private/tmp/vla_navigation_refactor_20261014/underlay/recovery_v196 \
  --workspace /private/tmp/vla-v201-rebuild
```

Run the following inside the existing `vla-newton-foxy:v149` image, with network
disabled, four CPUs, 6 GiB memory, the underlay root at `/task:ro`, the fresh
workspace at `/work`, and this version directory at `/version:ro`. Work in `/work`.

```bash
source /opt/ros/foxy/setup.bash
source /task/recovery_v196/install/setup.bash
export CMAKE_PREFIX_PATH=/task/recovery_v167/dependencies/osqp-install:$CMAKE_PREFIX_PATH
export MAKEFLAGS=-j2 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
colcon build --packages-select pct_planner lite3_nav2_interfaces scan_nav2_controller nav2_controller lite3_nav2_bridge lite3_nav2_plugins --executor sequential
python3 /version/tools/make_fixed_inputs.py --output /work/fixtures --building /task/global_coverage_v135_foxy/map.pickle
python3 /version/tests/compare_fixed_inputs.py --fixtures /work/fixtures --native-probe /work/build/lite3_nav2_plugins/pct_route_probe --legacy-python /task/recovery_v174/install/pct_planner/lib/python3.8/site-packages --report /work/fixed_input_report.json
source /work/install/setup.bash
export ROS_DOMAIN_ID=201 PCT_TEST_MAP=/work/fixtures/flat.pct
colcon test --packages-select lite3_nav2_plugins lite3_nav2_bridge --executor sequential --return-code-on-test-failure --ctest-args -R '^(test_direct_pct|test_mission_bridge|test_terminal_tree)$'
colcon test-result --verbose
```

The fixed-input comparison deliberately imports the old wrapper and loads its
old v174 native libraries. Its report records the actual `/proc/self/maps`
library paths. The C++ probe uses the rebuilt native library. This compares both
map preprocessing and path output against the prior implementation.

## Runtime interface changes

Export the selected tomogram once with `tools/export_pct_map.py source.pickle
destination.pct`. The binary `PCTMAP01` file has a little-endian header
`<8sIII5d`: magic, layer/X/Y dimensions, resolution, center X/Y, slice base and
slice spacing. It then stores six row-major float64 arrays in native InitMap
order and the original uint8 ground-validity mask. A sidecar JSON records hashes.
The runtime needs only the bundle; it does not load pickle or start Python PCT.

The navigation launch now requires `pct_map_bundle:=/absolute/map.pct` in place
of `pct_map`. The launch reads the same backend `nominal_body_height_m` for both
the input adapter and the planner's reference height.

HTTP goals retain `target_ground_xyz`; the adapter adds body height once.
`target_yaw_rad` is optional with a default of zero. The final Nav2 goal pose is
fixed by that input, rather than being rewritten from a PCT result. Status no
longer contains cached-path/canonical-planned-goal fields. Failures are returned
without replaying an old route. `/pct_planned_path` remains an observation topic,
now published by the C++ plugin.

Old v196/v197 runtime entrypoints remain untouched. The 1 Hz planning child and
v200 terminal completion remain unchanged; event-driven planning is a later step.
