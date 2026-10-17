# v206 remote build and fixed-input regressions

Local source of truth: this version plus its frozen v204 materializer chain.
Execution host: gpu5070ti, Linux x86_64. No compilation ran on the Mac.

Compose sources on the host (file copies and SHA-256 checks only):

```bash
python3 materialize_components.py --underlay UNDERLAY/recovery_v196 --workspace WORKSPACE
```

Reuse the immutable v204 fixed fixtures (`flat.pct`, `route-oracle.yaml`,
`building/terrain.json` and its payloads, `building_planner.yaml`,
`v196-navigate.xml`). Do not copy previously generated `component*` profiles.
Fixture regeneration commands are preserved in v203/BUILD.md and v204/BUILD.md.
Copy `v204/tools/prepare_component_profiles.py` and `tools/remote_build.sh` into
WORKSPACE. The source inventory covers every composed source file.

Transfer WORKSPACE to the fresh remote execution directory:
`/data/sun/vla_mppi_20261009/command_continuity_v206_20261015`.
The reusable Linux dependency tree is mounted read-only at `/task`; native
sources from the v204 composition are rebuilt, not copied from ARM64 installs.

```bash
docker run --rm --network none --cpus=8 --memory=16g \
  -v /data/sun/vla_mppi_20261009:/task:ro \
  -v /data/sun/vla_mppi_20261009/command_continuity_v206_20261015:/work \
  -w /work vla-mppi-foxy:v123-deps03 bash /work/remote_build.sh
```

The script verifies the full source inventory, builds all 14 exported packages,
generates component profiles, and runs the selected native/ROS regression suite.
It uses the existing `/task/recovery_v188/install` dependency chain and pinned
OSQP at `/task/recovery_v168/dependencies/osqp-install`.
No Newton process, physical navigation goal, training or robot is started.

The first build passed. One old goal-state test then advanced simulated time
1.33 s while retaining a previously complete stand sample, correctly failing
its unchanged 250 ms freshness gate. The fixture now samples the immediate
same-goal refresh without advancing time. `tools/remote_recheck.sh` rebuilds and
retests only the controller package; earlier logs/XML are retained in attempt01.

`verification/` holds the returned source gate, logs and test XML. The final
source/install/library identity receipt binds the Linux result to this version.
The host graph test is lightweight Python only:

```bash
python3 tests/test_native_graph.py
```

A successful component result does not validate physical speed, stability or
route completion. The last physical evidence remains v204 attempt01.
