---
origin: lead, direct read-only inspection of the rented 4090
date: 2026-09-11
label: surveyed
---

# Phase 0.1: what the rented 4090 already has

All findings below were read directly from the host (read-only); nothing was started, stopped, attached to or modified.
Route: `ssh -J gpu40901 rented4090`. Host clock is CST (UTC+8).

## The running container is identified

`sudo docker ps -a`:

    isaac-sim | nvcr.io/nvidia/isaac-sim:5.1.0 | Up 8 hours | created 2026-09-06 03:48:17 +0800 CST

Process: `/isaac-sim/kit/kit /isaac-sim/apps/isaacsim.exp.full.streaming.kit --no-window
--/persistent/isaac/asset_root/default=https://.../Assets/Isaac/5.1 --merge-config=/isaac-sim/config/open_endpoint.toml
--allow-root ... --/app/livestream/publicEndpointAddress=117.50.179.202`, started 06:31 UTC today, running as a
container-internal uid 1234.

It is **idle**: GPU 17 percent, 2,961 MiB of 24,564 MiB, and every Kit log except `omni.processlifetime.log` stopped
writing within a minute of startup. Its volume tree `/home/ubuntu/docker/isaac-sim/{cache,config,data,logs,pkg}` dates from
December 2025 / January 2026, so it predates this project's use of the machine.

Identity confirmed against `machine-dog/artifacts/2026-09-05_e01_rented4090_environment/README.md`, which documents this
same host (`ubuntu@117.50.179.202`) and states: "Existing `isaac-sim` container was preserved." The livestream endpoint in
the process arguments is that same IP. This is the vendor/base streaming instance, not something this project started.

Decision: leave it alone. It consumes 3 GB of 24 GB and 17 percent of the GPU, which leaves ample headroom, and we cannot
usefully share its process anyway.

## The important find: an Isaac Lab environment already exists here

`sudo docker images`:

| Image | Size | Age |
| --- | --- | --- |
| `v17a68-dependencies:20260905` | 27.1 GB | 5 days |
| `e01-walking-runtime:20260905` | 27.0 GB | 5 days |
| `e01-walking-isaaclab:20260905` | 26.0 GB | 5 days |
| `nvcr.io/nvidia/isaac-sim:5.1.0` | 22.9 GB | 10 months |

`e01-walking-isaaclab:20260905` is machine-dog's own Isaac Lab image, built on this machine on 2026-09-05 and recorded in
that README as verified: Isaac Lab **2.3.2.post1** with assets/tasks/RSL-RL wrapper modules, PyTorch 2.7.0+cu128,
NumPy 1.26.0, RSL-RL 3.3.0 and robot_lab 2.3.0 installed editable, TensorDict 0.7.2, Warp 1.15.0. Its recorded runtime smoke
ran 64 environments for 100 steps across five terrain columns with observation dimensions policy 450 / critic 373 /
single_obs 45 — the same contract the V12 policy uses.

Consequence for Phase A: **we do not build an Isaac Lab image.** We reuse this one and mount our own workspace. That matters
because the host has only 40 GB free of 194 GB and these images already occupy 30.4 GB; a 26 GB build would not fit
comfortably.

What differs from what we need, and therefore what Phase A must supply:
1. The E01 workspace holds `go2_rl_robotlab_lite3_v17a29` (the V17 line). We need the **V12** source and the
   `Wave-C-Stairs-V12-Lite3-v0` task registration.
2. The V12 checkpoint `model_149999.pt` must be vendored by SHA-256 (`a9d31dce...3d5450`, 26,367,345 bytes); it is
   gitignored upstream.
3. `integration/lite3_sim_bridge` is not present and must be imported.
4. The image's editable installs require the recorded workspace mount, so our workspace must follow the same pattern.

## Host facts for planning

- `ubuntu` has passwordless sudo (it is in `sudo`, not in `docker`, so docker needs `sudo`).
- Disk: 40 GB free of 194 GB; docker build cache holds 10.7 GB reclaimable and six exited machine-dog containers hold
  ~1 GB. **Those belong to machine-dog's work; this task must not reclaim them without Dr Sun's authorization.**
- GPU: RTX 4090, 24,564 MiB, currently 3,005 MiB used and 17 percent busy.
- The host renders: it is running a livestreaming Isaac Sim right now, so RTX rendering is available here. This is a
  favourable early signal for the Phase B go/no-go, though it is not yet a measurement.

## Open for Phase A

Whether `e01-walking-isaaclab:20260905` runs headless Isaac Lab with `enable_cameras=True`. The E01 work was training with
no cameras, so camera rendering inside that image is unproven. This is the first thing Phase B measures and the first thing
that could force an image change.
