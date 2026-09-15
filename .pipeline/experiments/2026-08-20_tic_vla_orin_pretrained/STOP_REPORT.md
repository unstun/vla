---
origin: ai_only
reviewed: false
---

# TIC-VLA Orin run stopped at the non-interference preflight gate

> Superseded on 2026-08-20: Dr Sun identified the DDS router as existing Lite3
> infrastructure and explicitly authorized the bounded offline TIC-VLA test to
> coexist with it. This report remains as the audit trail for the original stop.

## Outcome

The TIC-VLA CUDA inference was not run. The task stopped before source transfer,
dependency installation, model download, checkpoint download, model loading, or
forward execution because the Orin was not in the approved receive-only baseline.

## Triggered stop condition

The preflight process snapshot recorded both:

- an active root shell opened before this task's remote preflight; and
- a containerized persistent process
  `ddsrouter --config-path /etc/lite3/ddsrouter.yaml --log-verbosity info`,
  started at `2026-08-20 16:59:09` device-local time.

The same snapshot recorded DDS-style UDP listeners on ports `11811` and `11812`.
This is robot-related persistent communication state, so the explicit stop rule
applies. The task did not inspect the protected DDS configuration and did not
stop, modify, or interact with the process.

## Work completed before the stop

- Confirmed the Orin identity and CUDA runtime: Jetson AGX Orin, aarch64,
  Python 3.8.10, Jetson PyTorch 2.1.0, torchvision 0.16.1, CUDA 11.4.
- Confirmed approximately 62 GiB root storage remained available and CUDA was
  visible.
- Imported the exact upstream commit locally into the ignored pristine source
  path and verified its worktree was clean.
- Recorded SHA-256 values for all 386 tracked upstream files.
- Created only the approved empty remote task directory layout and its
  `manifests/preflight.txt` evidence file.

## Work not performed

- No Python dependency was installed.
- No base model or TIC-VLA checkpoint was downloaded.
- The checkpoint SHA-256 was therefore not measured.
- No checkpoint structure or state-dict compatibility report was produced.
- No CUDA model load, warm-up, measured forward, language output, waypoint
  tensor, latency, memory, temperature-under-load, or power-under-load result
  exists.
- No training, ROS/SDK command, robot command, network change, service change,
  or protected-file access occurred.

## Resume gate

Resume only after Dr Sun confirms that the active Lite3 DDS router/root session
is expected and explicitly authorizes this offline test to coexist with it, or
after a separately authorized operator places the Orin in a quiescent state.
The VLA task itself must not stop or reconfigure those processes.

## Evidence

- Full remote preflight: `manifests/preflight.txt`
- Local pristine file hashes: `manifests/local_pristine_sha256.txt`
- Upstream provenance: `../../../references/upstream/2026-08-20_tic_vla/repository_manifest.yaml`

This stopped run provides no TIC-VLA runtime claim. It does not represent a
paper reproduction, Lite3 integration, autonomous navigation, obstacle
avoidance, or real-robot safety validation.
