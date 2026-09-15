# Implementation plan

Ordered. Each phase ends in evidence that can be reviewed before the next starts. Remote runs need Dr Sun's authorization
per round, as in the camera ablation.

## Phase 0: resolve the pins and the machine (local + read-only remote)

- [x] 0.1 DONE 2026-09-11. The container is `isaac-sim`, image `nvcr.io/nvidia/isaac-sim:5.1.0` — the vendor/base
      streaming instance machine-dog's E01 work recorded as "preserved", idle at 17 percent GPU and 3 GB of 24 GB.
      Left untouched; nothing was started, stopped or attached to. Bonus find: `e01-walking-isaaclab:20260905`
      (Isaac Lab 2.3.2.post1 + robot_lab + rsl_rl, verified by machine-dog) is already on the host, so Phase A reuses
      it rather than building a 26 GB image onto 40 GB of free disk. Full record:
      `research/phase0-rented4090-isaac-environment.md`.
- [x] 0.2 DONE 2026-09-11. Bridge: VENDORED, not commit-pinned, because the code that produced the accepted 74 m run is
      uncommitted — `transport.py` in the working tree hashes to the `286f24e4...` recorded in `native_full02`'s
      executed-source manifest, while HEAD's is `652b74bc...`. 11 files vendored to
      `references/upstream/2026-09-11_lite3_sim_bridge/` (SHA256SUMS 11 OK), ROS/planner files deliberately excluded.
      machine-dog: pinned to `8c3fdffa84b85be0704a10ea5b2533817d543822` per the upstream locomotion manifest; the V12
      runtime must come from the 217-file recovered tree because the commit's 171-entry allow-list is incomplete.
- [x] 0.3 DONE 2026-09-11. Checkpoint identified and verified: `model_149999.pt`, 26,367,345 bytes, sha256
      `a9d31dce90e6e8c564d955e473d6d3502f893d7ef5a5c1efaf5bb50d6b3d5450`, matching the upstream manifest.
      STORAGE DECISION OPEN with Dr Sun: whether to duplicate the ~112 MB of V12 inputs into `vla` under a reviewed
      path-specific ignore (recommended), or leave machine-dog-nav as sole custodian and stage to the remote.
- [x] 0.4 Static check done 2026-09-11: `internvla_n1_agent_realworld.py` has zero habitat references, and neither
      `internvla_n1.py` nor `vln_utils.py` does either; the dependency surface is numpy, torch, transformers, diffusers, PIL.
      The two-process split stands and the VLA side needs an ordinary ML environment, not habitat-lab 0.2.4.
- [x] 0.5 DONE 2026-09-11. Live import succeeds: `InternVLAN1AsyncAgent` with
      `step(rgb, depth, pose, instruction, intrinsic, look_down)` and `trajectory_tovw(trajectory, kp)`, in a venv with
      zero habitat/isaac packages. The runtime prints "Habitat Evaluation is not loaded in this runtime" — upstream
      supports this mode explicitly. Correction to 0.4: the chain is larger than the file suggested (gym, pydantic,
      diffusers, numpy-quaternion, opencv-python, uvicorn, fastapi, transformers) because package inits import the
      Habitat agents; none of it is habitat-lab. Details and two packaging traps in
      `research/phase0-imports-and-pins.md`.

## Phase A: the base loop in our hands (Milestone A, AC1-AC2)

- [x] A.1 DONE 2026-09-11. Both imports already landed in Phase 0 and were completed here: the `robot_lab` Lite3
      assets (URDF, 17 STL meshes, the four official USD layers, `tasks/lite3/env_cfg.py`) ship inside the vendored V12
      runtime, and the bridge is the now 15-file `references/upstream/2026-09-11_lite3_sim_bridge/`. Corrected a Phase 0
      defect first: the 11-file bridge selection was NOT importable (four module-level `from .` targets were cut), so the
      first run would have died on `ModuleNotFoundError`; closure is now verified by AST walk. Experiment scaffold at
      `.pipeline/experiments/2026-09-11_lite3_isaac_v12_vla/` with `setup/inputs.json`, `setup/host_survey.json`, a
      verified 56.8 MB transport bundle (`488cb757...`, 233 files) and the stage/run scripts.
- [x] A.1b RESOLVED 2026-09-11. Dr Sun chose the rented 4090. My "the 4090 is missing isaaclab_tasks and
      isaaclab_rl" was WRONG: the PyPI `isaaclab` 2.3.2.post1 wheel bundles the whole IsaacLab source tree at
      `site-packages/isaaclab/source/`, and `find_spec` returned None only because those roots are not on `sys.path`.
      Four PYTHONPATH entries, no download, no image rebuild. Correction recorded in `research/phaseA-execution-host.md`.
- [x] A.2 DONE 2026-09-11 on the rented 4090, run `phase_a_flat_v4`: `--mode qualification --course flat`, the
      built-in 8.75 s scripted schedule, 9.03 simulated seconds in 24.8 s wall, adapter exit 0, inside the existing
      `e01-walking-isaaclab:20260905` image. Nothing was built, pulled or deleted, and the unowned `isaac-sim`
      streaming container was untouched (`containers_before/after.txt` are identical). Three earlier attempts are
      kept as evidence, `v1` being the important one: Isaac Sim died during extension start-up and still exited 0,
      so the driver now gates on the adapter's own report and rewrites a bare exit 0 into `rc=70 status=incomplete`.
- [x] A.3 DONE 2026-09-11. `command_observation_max_error` is **0.0 on all 451 recorded steps** - the commanded
      (vx, vy, wz) is bit-identical to the value in the policy's 450-dim observation at history offset 60, not merely
      inside the 1e-6 tolerance. Body response: vx 0.268 against 0.30 commanded, vy 0.151 against 0.18, wz 0.379
      against 0.40. `nonfoot_contact_max_n` 0.0, min root height 0.296 m, 99.3 percent supported samples, no
      termination, all finite, zero sequence gaps, exactly one watchdog event (the scheduled disconnect).
      `runtime_import_identity.json` proves the adapter loaded is `6104fe68...`, the module the accepted 74 m run used,
      and that `robot_lab`/`rsl_rl` came from the pinned V12 tree rather than anything installed in the image.
- [x] A.4 DONE 2026-09-11. All four runs collected to
      `.pipeline/experiments/2026-09-11_lite3_isaac_v12_vla/runs/<run_id>/` with per-run `manifest.sha256`, 0 non-OK.
      Written up in that experiment's `RESULT.md`.
- [ ] A.5 OPEN, reported not patched: the run self-reports `INSTRUMENTATION_ERROR`. The qualification telemetry sink
      consumed 0 frames because one read timeout kills it permanently - `FrameStreamClient.receive()` closes the
      socket on `OSError`, and `socket.timeout` is a `TimeoutError`, which is an `OSError`, while the sink loop treats
      a timeout as recoverable. Reproduced locally with stdlib only by `scripts/probe_sink_defect.py`. The defect is
      in `machine-dog-nav`, which a VLA task must not edit, and these bytes are hash-pinned to the accepted run.
      Phase A's criteria do not depend on it: the command evidence is computed in-process from the policy observation.

## Phase B: the robot can see — GO/NO-GO (Milestone B, AC3-AC4)

- [x] B.1 Add a robot-mounted RTX `CameraCfg` at the head pose, 640x480 HFOV 79, and launch with `enable_cameras=True`.
      Save a frame and confirm by eye that it is the robot's viewpoint, not the chase camera.
      DONE 2026-09-14 (`phase_b_single640_hz0_v1`, `phase_b_dual720_hz0_v1`): first-person and pitch sign verified by
      horizon rows and D435i depth. OPEN for Phase C: the head pose is approximate and the D435i pose is the adapter's
      sensor offset (29 % self-occluded); the measured mount transform is still required.
- [x] B.2 Measure: real-time factor and per-frame render time with cameras off, with one 640x480 camera, and with the full
      two-mount 720p configuration; peak GPU memory in each, and again with the VLA model resident.
      DONE 2026-09-14: see `.pipeline/experiments/2026-09-11_lite3_isaac_v12_vla/RESULT_PHASE_B.md`. With the VLA
      resident the Isaac probe hit an out-of-memory error (`phase_b_vla_resident_v2`); System 1 was not exercised.
- [x] B.3 Write the go/no-go. If the loop is not affordable on one GPU, name the fallback taken (resolution, render rate,
      render/physics decoupling, or a second GPU) before continuing.
      RESULT 2026-09-14: GO on one GPU (flat course) with F1 + F2 + autograd off + 640x480 input
      (`phase_b_vla_resident_v4`: 21,690 MiB device peak, System 1 exercised, Isaac RTF halves to 0.17 while sharing).
      Phase C must carry the six requirements listed in RESULT_PHASE_B.md; furnished-scene cost is re-checked in Phase D.
      WRITTEN: NO-GO on one 24 GB GPU as specified (F1-F5 in RESULT_PHASE_B.md).
      FALLBACK CHOSEN by Dr Sun 2026-09-14: F1 + F2, stay on one GPU. F1 = one-robot PhysX GPU buffers (the V12 task's
      512 MiB collision stack and Isaac Lab's 2**23 contact buffer are what failed). F2 = PyTorch expandable_segments
      for the VLA. Re-measure co-residence with System 1 exercised; if it still does not fit, return with F3.

## Phase C: the VLA drives (Milestone C, AC5-AC7)

- [x] C.1 Copy the bridge protocol into this task and add `IMAGE_FRAME_V1`; keep the clamp and watchdog behaviour intact.
      DONE 2026-09-14: `phase_c/lockstep_protocol.py` (+ `.diff`, `PROTOCOL_COPY.md`), `isaac_lockstep_server.py`; smoke
      run `phase_c_smoke_scripted_v1`. C.2 DONE as well: `vla_lockstep_client.py`, 4 local tests pass, independent review
      fixed 5 defects. C.3 DONE: `phase_c_red_box_v1` ran end to end (44 decisions, 28 s, model STOP) but missed the goal.
      See RESULT_PHASE_C.md.
      Refined 2026-09-14: add a lockstep step request (one 0.1 s tick, optional image). The Isaac-side runner is task-owned.
      It builds the V12 scene through the pinned adapter's `_configure_environment` as the Phase B probe did, adds the
      head RTX camera (640x480, HFOV 79, RGB + aligned depth), a chase camera and landmarks, and uses one_env buffers.
      Commands pass through the bridge's `LatestCommandState` and the contact guard as library modules, with the pinned
      adapter unmodified.
- [x] C.2 Write the non-ROS VLA client: receives image + body state, calls the agent with instruction/rgb/depth/pose/intrinsics,
      converts the trajectory with `trajectory_tovw`, sends `CMD_VEL_V1`. No edits to pinned InternNav source.
      Refined 2026-09-14 (Decisions 5-6): upstream MPC/PD at 10 Hz simulated ticks; latency-faithful lockstep; autograd
      off, `expandable_segments`, look-down follow-up, 640x480 input. CasADi comes from `pip --target` in the run root.
      Test locally against a fake simulator before any GPU run.
- [x] C.3 One episode end to end from a language instruction, bounded and supervised, with video plus a per-step log of
      instruction, System-2 output, trajectory, commanded velocity and measured body state.
- [x] C.4 A small bounded set of supervised episodes to characterise failure modes: falls, clamp saturation, and whether the
      0.2 s command-history lag is visible at the achieved VLA decision rate.
      Done 2026-09-14 over six episodes: red x4 (including C.3), blue, green (`RESULT_PHASE_C.md`, `analysis/`).
      - Locomotion held: 0 falls. The clamp and watchdog were never engaged or exercised.
      - Upstream MPC/PD limits bind instead.
      - Forward speed reaches 90 % in 240-440 ms, comparable to the 400 ms System 1 period; no failure traces to it.
      - Success 0/6, oracle success 1/6. Five runs passed the target sideways and said STOP with it out of view. Green
        struck the blue box's corner (514 N): body clearance, not a path into the box.
      - The first System 2 answer was `←←←←` in all six runs, whatever the instruction.
- [x] C.5 Lead review and evidence return.
      DONE 2026-09-14: accepted after corrections (`RESULT_PHASE_C.md`, "Lead review").
      - An independent read-only reviewer recomputed every number and raised 14 findings. Each was re-derived from the
        logs and applied.
      - Lead verdicts: AC5 met, AC6 met, AC7 met on this course. The PRD boxes are left for Dr Sun.
      - Sync gate: host code equals local.
      - Provenance: `setup/phase_c_executed_source.json`. The smoke run and red v1 ran client `c4c9694c`, recoverable
        with `setup/phase_c_client_c4c9694c_to_f6aa3b43.diff`.
      - Commit-gate ignore proposal: 30.1 MB tracked, 149.7 MB local-only. Not applied; decided at E.2.

## Phase D: a scene worth evaluating in (Milestone D, AC8-AC9)

- [ ] D.0 Body-clearance margin (PRD decision 4): survey and compare open-source footprint and clearance layers across
      three families:
      - navigation-stack layers;
      - safety filters and distance-field maps;
      - learned and legged-robot collision safety.

      Record URL, license, pinned commit, mechanism with source permalinks, inputs and outputs, ROS dependence, and fit
      between System 1 / MPC and the bridge. Output `.pipeline/survey/2026-09-14_body_clearance_margin_upstream_survey.md`.
      Dr Sun selects; nothing is imported or built before that.
      SURVEYED 2026-09-14: 5 candidates that address the failure; about 20 more screened out.
      - Recommendation: C (single-sample vs 32-sample-mean ablation, plus ground-truth clearance), then A (Nav2
        `collision_monitor` unmodified in a ROS 2 sidecar, with a simulated 360° LiDAR).
      - B (nvblox_torch + cbfkit) is the no-ROS alternative.
      - SELECTED by Dr Sun 2026-09-14: measure first, then Nav2 `collision_monitor` (design Decision 8).
- [x] D.0a Offline footprint clearance for the six Phase C runs.
      - Method: logged base pose and yaw against the URDF footprint (torso rectangle, and torso plus hip/thigh reach)
        and the box footprints.
      - Checks: minimum clearance, when and which side; the green episode must show about zero or negative clearance at
        the 17.9 s contact.
      - Local only; no GPU.
      DONE 2026-09-14 (`RESULT_PHASE_D.md`, `analysis/phase_d0_footprint_clearance.json`).
      - Minimum leg-width clearance: red 0.52-0.72 m, blue 0.22 m, green −0.022 m at the 17.90 s contact
        (torso-only 0.051 m, so a torso footprint misses it).
      - Green fell below 0.20 m 1.48 s before contact.
- [-] D.0b DROPPED 2026-09-14 (PRD decision 7: the model's limits are accepted, so the margin must be model-agnostic).
      Was: single sample against the 32-sample mean (needs Dr Sun's authorization for GPU runs).
      - Why new runs are needed: the Phase C logs keep only the mean path, and decision frames were saved every 5th
        decision, re-encoded, with no depth. So an exact offline replay is not possible.
      - Plan:
        - have the client log all 32 samples per System 1 call, instrumentation only;
        - add a switch that follows one sample;
        - rerun the green and red layouts in bounded, supervised episodes.
- [x] D.0c Nav2 `collision_monitor` sidecar, scripted tests. Environment route chosen by Dr Sun 2026-09-14: RoboStack
      Jazzy conda env, task-owned, no sudo or Docker.
      - ENV DONE 2026-09-14: `$ROOT/ros2_jazzy` via `scripts/phase_d_setup_ros2_env.sh`.
        - Contents: 409 packages, 183 MB download; `ros2-nav2-collision-monitor` 1.3.12, Python 3.12.
        - Installer: micromamba 2.1.1, binary sha256 0d2dd49f...
        - Lock, list, dry run, log and smoke log in `setup/phase_d_ros2_jazzy_env/`.
        - Smoke test: `collision_monitor` configured and activated (domain 87, localhost only), then stopped.
        - Disk: about 2.4 GB used, 18 GB left.
      - Reuse found (not built): the pinned bridge's MultiMeshRayCaster MID-360 LiDAR config and point packing, and
        `machine-dog-nav` `integration/lite3_sim_bridge/lite3_sim_bridge/foxy_bridge_node.py` @ `848b4aec`, which
        publishes `/clock`, odometry and PointCloud2 and forwards Twist.
      - Components: a simulated 360° LiDAR in the lockstep server; transport of `/clock`, odometry, point cloud and
        `cmd_vel` in/out; footprint and zone configuration from the URDF.
      - First test: the green layout. Pass criteria: no non-foot contact, stop on stale data, and success and oracle
        success reported beside clearance.
      - SCRIPTED TESTS DONE 2026-09-14 (`RESULT_PHASE_D.md` D.0c, `analysis/phase_d0c_monitor_summary.json`). Label:
        integrated, not validated (success and oracle success need VLA episodes).
        - Pre-GPU independent review: 3 should-fix items verified and fixed (lidar.reset() before each scan, relay
          per-tick fields, driver early exit); CPU re-rehearsed.
        - Six Isaac runs, all clean: G1 passthrough green replay = Phase C bit for bit (514 N FR_HIP 17.9 s); G1b/G2 on
          the reset server are identical until the monitor's first scaled command, G1b hits at 16.82 s, G2 no contact
          through 18.0 s (0.109 m); head-on and corner halted 0.103/0.099 m short; stale cloud STOP 0.40 s after the
          last cloud, 0.020 m to rest.
        - lidar.reset() deterministically changes the physics path (1.6 µm at step 7, 0.17 m by 16.8 s); mechanism
          unverified.
        - Known issue before next use: the driver's `pgrep -f` guard matched the launching ssh shell (one refused
          start, logged in `setup/phase_d_isaac_chain_20260914/`).
- [x] D.0d VLA episodes with the monitor in the loop. Authorised by Dr Sun 2026-09-14 (2-3 episodes). Pass criteria from
      D.0c: no non-foot contact, stop on stale data, success and oracle success reported beside clearance.
      - DONE 2026-09-14 (`RESULT_PHASE_D.md` D.0d; `analysis/phase_d0d_vla_summary.json`, `phase_d0d_monitor_summary.json`,
        `analysis/phase_d0c_figures/fig4_*`, `video3_*`). Label: integrated, not validated.
        - Green, red, blue: success 0/3, oracle 1/3 (red 0.83 m), no contact, 0 of 1,092 commands changed by the
          monitor; closest leg clearance 1.38 / 0.27 / 1.46 m. The model never drove at a box, so the monitor was
          not exercised by the VLA.
        - Driver `scripts/phase_d_run_vla_episode.sh` (pgrep guard fixed), CPU-rehearsed with the scripted client.
        - Found: the pitched LiDAR misses boxes behind the robot beyond about 2.8 m (empty clouds, handled as valid).
- [x] D.0e VLA episodes with the goal behind a box (Dr Sun 2026-09-14). DONE 2026-09-14 (`RESULT_PHASE_D.md` D.0e;
      episode `d_green_behind_grey_box_v1`; `analysis/phase_d0e_*`, `fig5_*`, `video4_*`). Label: integrated.
      - Three runs: all 60 s timeouts, no STOP, closest to target 2.95-3.12 m, closest to the grey box 0.85-0.94 m,
        0 of 1,803 commands changed, no contact.
      - System 2's first answer was identical in all three: look-down, then pixel goal `571 297` on empty floor right
        of the visible target; the robot swung right and wandered. Cause (level image in the look-down call?) UNVERIFIED.
      - Six VLA episodes with the monitor so far; none gave it anything to change.
      - Before running: fix the driver `pgrep` self-match; decide how the VLA client connects through the relay
        (images and the want_image path are forwarded, but untested with a VLA).
      - Watch for: static-polygon freeze (3+ points inside `FootprintApproach` zeroes every command), goals nearer an
        obstacle face than about 0.39 m being unreachable, and the scaled commands falling below the V12 deadband.
- [x] D.0f The real two-mount camera fusion in Isaac (design Decision 3, configuration 2). Authorised by Dr Sun
      2026-09-14 ("Proceed with Option 1: Run the real camera fusion in Isaac").
      - What: the Isaac server renders the stock head camera (1280x720, HFOV 105, +16.7 deg) and the D435i (1280x720,
        HFOV 69, colour + z-depth, 20 deg down), and fuses them with the unmodified Habitat `fused_camera.py`
        (sha256 382eee6d) into the c8 virtual camera: the existing level head_eval view, 640x480, HFOV 79. That fused
        image replaces the ideal render in IMAGE_FRAME_V1. Depth stays the ideal head_eval depth at the virtual pose,
        as in c8. The client, model, controllers, relay and episodes are unchanged.
      - Choices made here (stated, not measured):
        - D435i optical pose from the machine-dog-nav sensor-rig URDF (`lite3_pro_sensor_rig_real_with_interface.urdf`,
          untracked in that repository, so pinned by sha256 d0a1be09; sensor_carrier_joint + d435i_body_joint +
          d435i_depth_optical_joint): TORSO (0.2521, 0, 0.0740), 20 deg down.
          Not Phase B's (0.182, 0, 0.109), whose view is 34 % head shell. Relative to the estimated head pose
          (0.27, 0, 0.09) it sits 0.018 m behind and 0.016 m below; c8 put it 0.02 m behind and 0.02 m ABOVE. Neither
          transform has been measured on the robot.
        - Fusion runs inside the Isaac container (cv2 4.11.0 and numpy 1.26, as in the Habitat c8 runs); its wall time
          pauses the simulator, so it does not change what the robot experiences.
        - Unlike Habitat, the robot body exists here: whatever part of the V12 Lite3 mesh the D435i sees is reported
          as self-occlusion, not hidden.
      - Code: `phase_d/isaac_fusion.py` (glue: TORSO/ROS poses to the fusion frame, intrinsics check, per-frame
        statistics), `phase_d/fusion_isaac_c8.json`, `--fusion-config` on the server (off by default), `VLA_FUSION=c8`
        on `scripts/phase_d_run_vla_episode.sh`. Local synthetic test renders the three cameras independently in the
        Isaac convention and requires the fused image to match the ideal render.
      - Gate before any VLA episode: an independent code review, the synthetic test, then Isaac run 1, a scripted-agent
        preflight on the green layout. It must meet the Habitat c8 preflight bounds on every decision frame (uncovered
        <= 4 %, head share >= 70 %, mean abs error vs ideal <= 10 head region and <= 20 D435i region), pass the
        intrinsics check, and keep Isaac at <= 6,000 MiB. The images must also pass my visual check. If it fails,
        stop and report; do not tune the bounds to pass.
      - Runs (at most 6 Isaac starts, stop at the first abnormal run):
        1. `phase_d_fused_scripted_preflight_v1` (green, scripted agent);
        2-4. `phase_d_vla_fused_{green,red,blue}_box_v1` (compare with D.0d);
        5. `phase_d_vla_fused_green_behind_box_v1` (compare with D.0e v1-v3);
        6. spare, only for a start that fails before simulation; never to re-roll an outcome.
      - Claim boundary: one episode per layout, unseeded System 1, System 2 route lock: effect sizes only. The label
        stays integrated.
      - Pre-GPU review 2026-09-14 (independent agent, review only): no blocking code defect; 2 must-fix evidence gaps
        and 5 should-fix items, all verified and fixed before run 1:
        - lossless raw inputs for saved decision images, and `phase_d/fusion_recompute_check.py` run by the driver in
          the same image after each episode (bit-identical re-fusion; the client's first frame is the fused image);
        - each camera's TORSO-relative pose read back from Isaac (`check_mount`, 2 mm / 0.1 deg) next to K;
        - gate bounds pinned in `scripts/phase_d0f_fusion_summary.py` (a run's recorded bounds must equal them), video
          frames gated too, one decision row per image sent;
        - `VLA_SCRIPT` whitelisted; config and module hash checked before Kit starts; the chain re-runs the gate on
          the host and stops on any out-of-bounds decision frame or failed recompute.
        - The test now also flips the forward and lateral signs of the pose conversion: the forward flip gives D435i
          error 15.8, inside the c8 bound of 20, so the tighter self-test bound (12) is what catches it.
        - Checks: synthetic test 13/13 locally and in the container; fake-run gate passes a good run and rejects a
          tampered pixel, a client given the ideal image, and loosened recorded bounds.
      - Run 1 `phase_d_fused_scripted_preflight_v1` (start 1 of 6): REFUSED by the new mount check before serving any
        image. Every camera, head_eval included, read 3.99 deg and 3.7 cm from its configured TORSO pose. Cause,
        verified in Isaac Lab 2.3.2 source: `CameraCfg.update_latest_camera_pose` defaults to False, so
        `data.pos_w`/`quat_w_world` stay at the initialisation pose from before the robot settled
        (`sensors/camera/camera.py:499-501`, `camera_cfg.py:77-83`). Rendering follows the robot; only the reported
        pose is stale. Fix: refresh once through `_update_poses` (Fabric world poses), check, restore the buffers; an
        unrefreshed pose fails the gate instead of refusing.
        - Side finding: every Phase C/D IMAGE_FRAME_V1 carried that stale initial camera pose. No effect on behaviour:
          the upstream real-world agent accepts `pose` and never uses it, and the client transforms trajectories with
          BODY_STATE odometry. Metadata defect, recorded, not fixed (a fix would change the D.0d/D.0e pipeline).
      - Run 2 `phase_d_fused_scripted_preflight_v2` (start 2 of 6): REFUSED again, errors now smaller and different
        per camera, all refreshed from the simulator: head_eval 7.8 mm / 0.11 deg, fusion_head 23.5 mm / 0.33 deg,
        fusion_d435 27.4 mm / 0.50 deg, almost all in z. head_eval and fusion_head share the parent prim and the
        local translation (0.27, 0, 0.09) and differ only in local rotation, so their true positions are identical;
        the readback puts them 15.6 mm apart. The live-pose readback is therefore not a same-instant measurement
        (mechanism UNVERIFIED), and cannot validate the mounts. STOPPED here, as promised; host clean. Awaiting Dr Sun.
      - CORRECTION from Dr Sun 2026-09-14: the URDF is accurate, and on the robot the D435i sits ON TOP, tilted down,
        above the built-in camera. The D.0f config contradicts that: the built-in camera pose (0.27, 0, 0.09) is the
        camera ablation's estimate (the URDF has no built-in camera frame), which puts the URDF D435i (z 0.074)
        0.016 m BELOW it. I flagged the mismatch in the plan but ran anyway instead of asking. The built-in camera
        pose (and pitch: recorded +16 +/- 2 deg up, described by Dr Sun as almost horizontal) must be settled with
        Dr Sun before any further run.
      - DECIDED by Dr Sun 2026-09-14: built-in camera at the c8 offset from the URDF D435i, TORSO (0.2721, 0, 0.054),
        0.02 m ahead of and 0.02 m below the D435i; pitch +16.7 deg up (measured); evaluation view at that optical
        centre (config `virtual`; head_eval 0.036 m lower than in Phase C/D.0d/D.0e). Outside the V12 torso.STL, about
        1.6 mm in front of the head face. Synthetic test with it: head 77.2 %, D435i 20.0 %, uncovered 1.21 %, errors
        1.69 / 2.23, against Habitat c8's real-render preflight 77.3 % / 20.0 % / 1.23 %.
      - Mount check changed: enforce the camera prim's authored local pose relative to TORSO (USD translate/orient,
        0.1 mm / 0.01 deg) and K; record the Fabric world-pose readback at episode start and end for diagnosis only.
        Gate rejects a 1 mm D435i authoring error (fake-run test).
      - Budget: preflight v3 is start 3 of 6; the chain runs green, red, blue (starts 4-6). The goal-behind-box
        episode needs a 7th start from Dr Sun.
      - Run 3 `phase_d_fused_scripted_preflight_v3` (start 3 of 6): GATE PASSED (host and local). 11 decisions, 4.3 s,
        client_end; 12 decision and 43 video frames all inside the c8 bounds; uncovered 1.00-1.11 %, head share
        77.2 %, error vs ideal head 1.16-1.49 and D435i 1.85-2.21; D435i self-occlusion 0; fusion 196-266 ms;
        authored mounts exact (9e-9 m, 0 deg); recompute bit-identical and the client received the fused image; Isaac
        peak 4,198 MiB. Visual check: boxes and floor lines aligned across the seam; the difference image shows only
        one-pixel outlines on all sides of edges (`analysis/phase_d0f_figures/fig0_*`, composed inline, to be moved
        into a figure script).
        - The live readback (record only) gave the SAME per-camera errors at start and end, and the same values as v2
          (7.8 mm / 0.108 deg, 23.5 mm / 0.329 deg, 27.4 mm / 0.504 deg) although the robot walked in between and the
          built-in camera moved 0.036 m. So it is a constant per-camera readback bias, not staleness; my v2 wording
          ("not a same-instant measurement") was wrong about the mechanism, which remains UNVERIFIED.
        - Limit: the flat course is almost textureless, so the mean-error bounds are weak evidence of sub-centimetre
          registration; the authored-mount check and the synthetic test carry that claim.
      - Chain started 2026-09-14T18:10:56Z (host gate re-run PASSED): green, red, blue.
      - DONE 2026-09-14 (`RESULT_PHASE_D.md` D.0f; `analysis/phase_d0f_fusion_summary.json`,
        `phase_d0f_monitor_summary.json`, `analysis/phase_d0f_figures/`). Label: integrated. All 6 starts used.
        - Green/red/blue with the fused camera: all driver/relay/client/recompute exit codes 0; 181 decision and
          1,144 video frames inside the c8 bounds; recompute bit-identical; client received the fused image.
        - Success 0/3, oracle 0/3 (ideal D.0d 1/3); closest 1.23 / 1.67 / 1.30 m (ideal 1.99 / 0.83 / 2.00); every
          run said STOP after passing the target, ending 5.1-12.2 m away; 0 commands changed; no contact; red passed
          the green box at 0.14 m leg clearance.
        - First System 2 answers changed on green and red; one run per layout and two simultaneous changes (fusion,
          view 0.036 m lower), so no attribution.
        - Open for Dr Sun: a 7th start for the goal-behind-box layout with the fused camera.
- [x] D.0g Offline (no GPU), asked by Dr Sun 2026-09-14: can System 2 act as the eyes and give a target coordinate?
      `scripts/phase_d_pixel_goal_grounding.py` over the 148 pixel-goal answers of the 15 collected Isaac VLA runs.
      DONE 2026-09-14 (`RESULT_PHASE_D.md` D.0g; `analysis/phase_d_pixel_goal_grounding/`):
        - target visible in 42 answers; no goal on the box, median bearing error 25.1°, floor estimate median 2.16 m
          from the target centre (2 of 26 within 1 m);
        - favourite coordinates repeat across runs, and the same ones lead the Habitat castle runs;
        - arena-only; every answer followed a look-down that re-used the level image.

- [ ] D.1 Select a furnished interior and run the collision/performance admission check that the nav survey defines but never
      executed. Record the result either way.
      SELECTED as next step by Dr Sun 2026-09-14 (scene and start budget still open). PROPOSED plan, not yet authorised:
      - Gate source: `machine-dog-nav/.pipeline/survey/2026-08-16_isaac_lab_indoor_campus_scene_chatgpt_leads.md`
        "Minimum Admission Gate" (provenance, collision, Lite3 physical, sensor, route; route is D.2).
      - Prior evidence is visual only, and from another project on another machine: machine-dog-nav's 2026-08-16 preview
        ran on an RTX 5070 Ti (`machine-dog-nav/.pipeline/experiments/2026-08-16_isaac_indoor_scene_preview/`). No
        furnished scene has been loaded on this task's rented 4090, so those results are hints, not 4090 evidence.
      - Candidates (S3 folder listing 2026-09-14; references outside the folder not yet counted):
        - Office: 706 MiB. In that preview the full scene rendered no first frame; a 4 m subset and a floor-by-floor tour
          did.
        - Hospital: 1,047 MiB. In that preview only a 4 m clay subset rendered; the 8 m subset gave no first frame in
          10 min.
        - Simple Warehouse: 513 MiB. In that preview the full scene rendered; 792 meshes, all with CollisionAPI.
      - D.1a Pin and fetch: one download to the host under the run root, with a manifest (S3 key, size, ETag, SHA-256).
        No NVIDIA asset enters this repository.
      - D.1b Stage audit start, no robot and no VLA:
        - references resolve from the local copy;
        - metre scale and Z-up, one PhysicsScene, no duplicate ground;
        - CollisionAPI inventory for the chosen region;
        - first frame from both fusion cameras, and GPU memory.
      - D.1c Collision and Lite3 physical gate: rigid probes on key furniture; the Lite3 stands, walks, turns, and makes
        low-speed wall and desk contact with no penetration and no hidden reset.
      - D.1d Performance start with InternVLA-N1 resident and fused cameras: peak GPU memory and RTF, on the flat course
        21.9 of 24.6 GiB.
      - Blocker to raise: the unowned vendor `isaac-sim` container was running and holding 2.9 GiB on 2026-09-14.
      - Thresholds must be frozen here before any start.
- [ ] D.2 A Lite3 reference route in that scene with no non-foot contact.
- [ ] D.3 Author at least two evaluation episodes whose instructions name visible furniture, with goal positions and a
      success radius, so success is measurable.

## Phase E: close out

- [ ] E.1 Spec update: what this task learned that belongs in `.trellis/spec/backend/`.
- [x] E.2 Commit after Dr Sun reviews the staged path list.
      DONE 2026-09-15 for Phases A to D.0g. Dr Sun approved the review table in task 09-14-commit-backlog-evidence,
      and this task's text evidence was committed as commit 9 of 10 there. Frames, videos, depth arrays and figures
      stay local-only: `.gitignore` block plus `LOCAL_ONLY_BYTES.sha256` in the experiment directory. Work from D.1 on
      is committed separately.

## Validation commands

    python3 ./.trellis/scripts/task.py current
    # Phase 0.4, the cheap de-risking check:
    python3 -c "import sys; sys.path.insert(0, 'references/upstream/2026-09-08_dualvln/source/InternNav'); import internnav.agent.internvla_n1_agent_realworld"

## Review gates

Phase A evidence before Phase B. The Phase B go/no-go before Phase C. Dr Sun's authorization before every remote round, and
before anything runs on the machine hosting the unowned Isaac container.
