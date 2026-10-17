# Factory control library: initial load-stage record

Current follow-up: the original algorithm has now driven a local Newton
crouch/zero-return-torque/stand episode. Strict calibration and in-place checks
remain unmet. See `SIMULATION_RESULT.md`, `ALGORITHM_ABI.md` and
`video_delivery.json`. The record below describes the earlier load-only stage;
its "not yet run" statements are historical, not the current execution status.

Stage: experiment + analysis, 2026-09-27. Scope: user-authorized read-only SSH
inspection and one isolated local library-load check. Factory homing has not
been executed or reproduced in Newton.

## Verified result

The robot at the authorized SSH target is running Ubuntu 20.04.5 LTS on an
ARM64 Rockchip RK3588 board. Process 601 (`jy_exe`) remained running throughout
the inspection. Its readable command path and the service startup script both
select `/home/ysc/jy_exe/bin/jy_exe`, a symlink to `bin/backup/deeprcs`.
The copied executable contains version string `Deeprcs Version: 2.0.158(158)`.

There are older, different executable/library files at the package root.
They were retained separately; they were not substituted for the startup-selected
version. Exact identities are recorded in `source_manifest.json`:

| Selected artifact | SHA-256 |
|---|---|
| `bin/jy_exe` / `bin/backup/deeprcs` | `33ea6a7da1a541c35d55833bb58894bf188d409456b5fafdbaf6057330a77426` |
| `lib/ras_lib/libdeepras.so` / `bin/backup/libdeepras.so` | `782a23d194f7e578b04f65beada1e003acd8d6be6a5b0fe1d115c8a77a542a3a` |

The live root-owned process's `/proc/PID/exe`, `maps` and `fd` require more
privilege than this SSH account has. Noninteractive sudo required a password.
No password was guessed, no permissions were changed, and no debugger was
attached. Therefore the selected library follows the recorded filesystem and
startup dependency chain; its identity as the library currently mapped in the
live process is not independently confirmed.

## A separable algorithm interface exists

The selected library exports:

- `MotionInitial(string const&, string const&, MotionConfig const&)`;
- `Motion(DataLegs const*, DataGyro const&, double const&, double const&,
  ControlCommands const&, double (*)[140], DataLegs*)`.

It also exports `basic_motion::BasicMotion::MotionProcess()` and its movement
helpers. The main executable contains distinct motor and sensor adapters,
including `RtCan`, `MotorCan`, `MotorSpi` and IMU handlers. Static inspection of
`RtCan::init_can()` shows socket/bind/ioctl operations; the binary also contains
SPI, serial and CAN device names. The presence of each driver does not prove
that every driver is active on this particular robot.

The executable retains DWARF type information referring to the original
`robot_common/lib/ras_lib/types/ath_types/external_type.h`. The corresponding
source tree is absent/empty on the inspected device. The debug information
provides verifiable interface layouts:

| Type | Bytes | Verified contents |
|---|---:|---|
| `DataLegs` | 288 | Four-leg position, velocity and torque groups |
| `DataGyro` | 72 | Roll/pitch/yaw, angular rates and accelerations |
| `MotionConfig` | 216 | Controller configuration fields |
| `ControlCommands` | 552 | Includes `is_zeroposition` at byte offset 73 |

`is_zeroposition` is a verified field name and offset, not yet an established
request/completion contract. Likewise, units, leg/joint ordering, sign/offset
conversion, both time arguments, initialization strings and the diagnostics
array's required extent must be verified before calling the algorithm. Do not
fill ambiguous inputs with guessed values and call the result factory homing.

## Direct local load test

The original, unchanged control library and its selected dependencies loaded
successfully in an existing ARM64 Ubuntu 20.04 container. Both algorithm symbols
resolved. The test **did not invoke either algorithm function**, run the factory
executable or connect a physical/simulated motor interface.

- Image: `sha256:1c102582b40d5305e310788c79e963e4b6cde13aea2bc5db3b7c1800e821935d`.
- Container network: `none`; passed-through devices: none.
- Read-only root and snapshot mounts; no Linux capabilities; non-root user;
  no-new-privileges; 512 MiB memory limit; one CPU; 64-process limit.
- Deadline: 30 seconds. Exit code: 0. No timeout or OOM.
- Python-reported peak resident size: 97,496 KiB. This is not a full algorithm
  or simulation resource measurement.
- The temporary container was removed successfully after recording its state.

Commands, stdout, stderr and container-state evidence are in
`library_load_check/`. `library_load_probe.py` contains only dynamic loading and
symbol lookup. `run_library_load_probe.py` records the isolation and cleanup.
PyTorch, ONNX Runtime, logging and OpenMP dependency files were copied read-only
and hash-checked; see `dependency_manifest.json`.

## Implication and remaining work

The earlier dependency “obtain the internal program” has been resolved for this
bounded inspection. It is now plausible to keep the factory **algorithm library**
unchanged and replace the external hardware I/O with a simulator adapter.
This is an engineering inference from the exported interface plus the successful
load check, not proof that a complete homing episode works outside the robot.

The recommended next experiment is local and isolated:

1. Recover and cross-check the full ABI and the application's actual input
   conversion/initialization at the `Motion` call site.
2. Identify how a factory return-to-zero request reaches that interface, and
   whether any essential encoder calibration or handshake remains in the motor
   driver/firmware layer.
3. Run a bounded synthetic-input algorithm check without physical networking,
   preserving the original library bytes. Record actual phase/output behavior.
4. Only after that contract is established, supply Newton's measured joints/IMU
   and apply the returned commands under one continuous physical state. Compare
   against an appropriate factory reference before delivering a homing video.

The entire factory executable is not the preferred first integration target:
it starts hardware/network services and changes hardware runtime settings via
its startup script. Reusing the discovered algorithm seam avoids importing those
unrelated host operations into Newton.

## Preservation and claim boundary

Raw binaries/configuration stay only under the exact ignored `private_snapshot/`
directory. No redistribution license is established; the audit is not an
open-source release. Provenance, hashes, acquisition scripts, ABI findings and
test results remain visible in the repository.

No robot service was started, stopped or restarted; no config, network setting
or calibration value was changed; no motor-control or homing command was sent.
The end-of-inspection evidence checks process continuity and selected file hashes.
Current status: **library-load verified; factory homing and Newton integration
not yet validated**.
