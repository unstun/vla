# v210: full navigation with v208 locomotion

**Passed one original-start full-route physical trial on gpu5070ti.**
Run: `v210_linux_full_attempt01`. Frozen navigation: v206; locomotion: v208.
No navigation algorithms, parameters, retry policy or endpoint rules changed.

- Physics: 137,000 actual integrations; 137.005 s.
- Original full-route verifier: passed, including continuous original-start
  history, original goal, position, height, yaw, shared-state and fixed PD.
- Final XY error: 0.126414 m; height error:
  0.001511 m; yaw error: 0.101797 rad.
- Final fixed PD begins at 132.654 s and lasts
  4.351 s through the final recorded sample.
- PD owns all joints; Kp/Kd remain 60/1 throughout that interval. Final command
  is exactly zero; measured linear/angular speed is
  0.0001971 m/s / 0.0000533 rad/s.
- Final FL/FR/HL/HR forces: 35.35, 54.53, 17.16, 23.26 N.
- No fall reported; minimum recorded torso up-vector Z: 0.850721.
- Navigation actual RTF: 0.999992. Native local planning averaged
  22.59 successful rounds/s; this is not
  a steady 30 Hz performance acceptance.

The actual graph-enabled robot passed a zero-step adapter/factory-handoff check.
The unchanged 14-package native install passed binary/dependency identity checks
and a 12-second real ROS graph preflight. No C++ rebuild was needed. v208's
10 candidate and 53 parent tests are inherited prior evidence, not newly rerun.

The existing full-route verifier changes only the integration identity and
report label; its behavioral predicates remain unchanged. This is one passing
full-route trial, not repeated-run or new-terrain qualification. Earlier v206
full-route failure, v208 short comparisons and all frozen sources are preserved.

## Evidence and reproduction

[Full-route gate](results/full_route_verification.json) ·
[Final PD hold](results/final_hold.json) · [Outcome](results/outcome.json) ·
[Runtime adapter](results/locomotion_activation.json) · [Manifest](manifest.json).

Local source is this VLA repository. Remote execution copy:
`/data/sun/vla_mppi_20261009/repo`; native install:
`/data/sun/vla_mppi_20261009/command_continuity_v206_20261015`.
Run `versions/v210/launch.py` with the Newton worker Python on gpu5070ti.
The fixed run ID is immutable and a second launch refuses an existing output.
A repeat requires a separately authorized attempt identity, not overwriting.

Raw capture remains at `/data/sun/vla_mppi_20261009/trials/v210_linux_full_attempt01/runs/v210_linux_full_attempt01/raw_capture.zip`,
372,476,880 bytes, SHA-256 `72cafc01a01ff4170a932161723cc659c7e47d37dba61e2df5a5a2baa35ba64c`; all
1263 archived members verified. Run
`versions/v210/analyze_full.py` there to reproduce the compact analysis.
Video is generated separately by the display-only v211 entry.
