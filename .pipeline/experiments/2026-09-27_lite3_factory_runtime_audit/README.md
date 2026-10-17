# Lite3 factory runtime: read-only acquisition and local simulation test

Stage: experiment + analysis. Date: 2026-09-27.

Current result: the original library now drives Newton through crouch,
zero-return torque and standing. Strict calibration and in-place checks remain
unmet. Start with `SIMULATION_RESULT.md`; `ALGORITHM_ABI.md` records the verified
seam and `video_delivery.json` identifies the real MP4. Dr Sun's subsequent
request authorized this bounded local test. Physical access remains read-only.

Dr Sun authorized SSH access to the powered-on Lite3 to investigate running the
factory control program against simulation. This permits this read-only source
and binary inspection; it does not authorize physical homing, actuator takeover,
service restarts or configuration changes.

## Scope and evidence

The local VLA repository is the source of truth for the audit. The robot is an
observed source device at the user-authorized SSH target, not an execution copy
to be modified. Read-only queries identified Ubuntu 20.04.5/aarch64 on a
Rockchip RK3588 board, with factory process `jy_exe` running as root.

The process's readable argv[0] is `/home/ysc/jy_exe/bin/jy_exe`. That path resolves
to `bin/backup/deeprcs`; the startup script selects the same path. A distinct
older executable and library also exist at the root of `jy_exe`. Do not mix
these versions. `/proc/PID/exe`, `maps` and `fd` could not be read as the SSH
user, and noninteractive sudo required a password. No privilege or service
configuration was changed. A mapped-library identity claim remains unverified.

Exact selected binaries and configuration are saved under `private_snapshot/`
for local inspection and isolated algorithm execution. Redistribution license is not established;
the directory has one path-specific ignore entry. Track the source manifest,
file sizes, hashes, collection times, retrieval command and analysis results
outside it. The snapshot is not an open-source import and must not be published.

Re-acquisition uses the read-only collector recorded in this directory and the
existing SSH authentication. It reads only the explicit file allowlist. The
manifest records resolved remote paths and local hashes. Re-acquisition from
a later firmware may differ; preserve the original snapshot and compare hashes
rather than silently overwriting it.

## Initial acquisition boundary

1. Pin the relevant runtime bytes and startup identity without executing them.
2. Inspect ELF dependencies, exported control functions and motor/sensor I/O.
3. Locate homing implementation or the missing lower-level firmware interface.
4. State what remains necessary for a local isolated software-in-the-loop test.

If the static interface is separable, a bounded local library-load check may use
an already installed ARM64 Linux image, with no network, no devices, all
capabilities dropped, read-only snapshot mounts and a wall-clock timeout. This
only checks dynamic loading; do not invoke motor drivers or the full factory
executable. It is not a homing or Newton validation result.

Do not execute the factory startup scripts, load the factory library on the
robot, attach a debugger to the live process, send a command to a motor/control
socket, bind a telemetry port or change calibration/network settings. No new
motion is required for this audit. Existing SSH reads and local static tools
are sufficient for the initial scope.
