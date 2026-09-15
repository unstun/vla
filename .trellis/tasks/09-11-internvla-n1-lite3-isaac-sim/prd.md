# InternVLA-N1 driving a Lite3 in Isaac Sim

Stage: planning. Opened 2026-09-11 on Dr Sun's instruction, "let's focus on getting the simulation fully ready first"
followed by his choice of the Isaac Sim route and "yes, create the task and start planning".

## Why this task exists

The Habitat ablation (`09-10-internvla-n1-camera-ablation-sim`, 45 runs) measured what InternVLA-N1 DECIDES: where it goes
and when it stops. It cannot measure whether a Lite3 could carry those decisions out, because Habitat has no robot. Its agent
is the stock `rgbd_agent`, a camera that teleports 0.25 m per step and turns 15 degrees at a time on a navmesh, with no
body, no legs and no dynamics. The discrete action space is a Habitat artifact: the model's own non-Habitat agent emits a
trajectory that upstream reduces to a body velocity (`internvla_n1_agent_realworld.py`, `trajectory_tovw`), and the Lite3
locomotion policy consumes exactly that 3-vector. The execution half of the pipeline has never been tested.

Survey of what already exists: `.pipeline/survey/2026-09-11_lite3_isaac_vla_integration/README.md`.

## Requirement

A Lite3 walks in Isaac Sim, driven by InternVLA-N1 from a natural-language instruction, with the model's own velocity output
as the only control path and robot-mounted rendered RGB as its only visual input; with recorded, verifiable evidence of each
run.

## Non-goals

- Real-robot actuation. Nothing in this task touches the Lite3 hardware.
- Training or fine-tuning of anything: the locomotion policy and the VLA are both used as pinned artifacts.
- Editing `machine-dog` or `machine-dog-nav`. Both stay read-only references (AGENTS.md); this task imports from them.
- Replacing the Habitat evaluation. That remains the decision-quality benchmark; this is the execution benchmark.
- Real sensor fidelity: MID-360 scanning behaviour, true D435i noise, LIO, localisation drift. Pose is simulator truth here.
- A performance claim against any published benchmark. This is a functional integration.

## Constraints

1. `machine-dog` and `machine-dog-nav` are read-only. Import by pinned commit; the V12 checkpoint is gitignored
   (`references/locomotion/.gitignore:1:**/source/`) so it must be vendored by SHA-256 with recorded provenance.
2. Both sibling repositories are currently dirty and `machine-dog-nav` HEAD sits on `codex/scan-foxy-isaac`, not main. A dirty
   worktree is not a runtime source; resolve the pin before importing.
3. Remote execution on a rented GPU needs Dr Sun's authorization per round, as in the camera ablation. Long runs are bounded
   and supervised.
4. An Isaac Sim container is already running on the rented 4090 (`/isaac-sim/runheadless.sh`,
   `isaacsim.exp.full.streaming.kit`). Its owner is not documented in either repository. It must not be disturbed, and its
   identity must be established before anything runs there.
5. No model or evaluator source edits to the pinned InternNav, consistent with the camera-ablation discipline: adaptation
   happens in this repository's own code.
6. Evidence returns to local paths with manifests and SHA-256, and a remote-only success is not evidence.

## Acceptance criteria

Milestone A — the base loop works in our hands, no VLA.
- [ ] AC1 A Lite3 walks in Isaac Sim under a scripted velocity command, from a pinned import of the V12 policy and the Isaac
      adapter, with recorded body travel, contact forces and clean exit. Provenance records the pinned commits and the
      checkpoint SHA-256.
- [ ] AC2 The command path is proven: a commanded (vx, vy, wz) is shown to arrive in the policy observation unchanged, using
      the adapter's own command-evidence check.

Milestone B — the robot can see. This is the go/no-go.
- [ ] AC3 A robot-mounted RTX colour camera is attached at the measured head-camera pose and renders in the loop; a frame is
      saved and is visibly the scene from the robot's viewpoint, not a chase view.
- [ ] AC4 The cost of rendering is measured: simulation real-time factor and per-frame render time with cameras on versus
      off, and peak GPU memory with the VLA also resident. A written go/no-go on whether the closed loop is affordable on one
      GPU, with the fallback (lower resolution, lower render rate, or two GPUs) named if it is not.

Milestone C — the VLA drives.
- [ ] AC5 InternVLA-N1 receives instruction + rendered RGB + depth + pose + intrinsics and produces a trajectory, and the
      adapted `trajectory_tovw` output is written as (vx, vy, wz) through the bridge's existing clamp and watchdog path.
      AMENDED 2026-09-14 (Dr Sun): the velocity comes from upstream's real-robot controllers, not `trajectory_tovw`. The
      MPC tracks the trajectory, the PD controller executes arrow actions, both at 10 Hz as in
      `scripts/realworld/http_internvla_client.py`, and the result still passes the bridge's clamp and watchdog.
      `trajectory_tovw` is logged for comparison. See design Decision 6.
- [ ] AC6 One full episode runs end to end from a language instruction with the robot walking, recorded as video plus a
      per-step log of instruction, System-2 output, trajectory, commanded velocity and measured body state.
- [ ] AC7 The failure modes are characterised over a small bounded set of supervised episodes: whether the robot falls,
      whether commands saturate the clamps, whether the 0.2 s command-history lag matters at the VLA's decision rate.

Milestone D — a scene worth evaluating in.
- [ ] AC8 A furnished interior with validated collision is selected and a Lite3 walks in it without non-foot contact on a
      reference route; the admission check is recorded.
- [ ] AC9 At least two evaluation episodes exist with instructions that reference visible furniture, plus goal positions and
      a success radius, so that success is measurable rather than anecdotal.

## Decisions taken (Dr Sun, 2026-09-11)

1. **Machine: the rented 4090.** Its already-running Isaac Sim container must still be identified before anything runs, and
   must not be disturbed (Phase 0.1).
2. **Pinning: clean commits where files are tracked and clean, SHA-256 vendoring for the rest**, with provenance recorded.
   This covers the gitignored V12 checkpoint and anything else that is dirty or untracked upstream.
3. **Phase D scene: deferred.** It does not block Phases A to C.

Added by Dr Sun on 2026-09-14, after the C.5 review:

4. **Body-clearance margin in Phase D: yes, but not hand-built.** Phase C's green episode showed the point-model MPC
   walking the robot's hip into a box corner. Phase D adds a margin for the robot's footprint between the VLA's output
   and the bridge. It must come from an existing open-source implementation, chosen by comparing several GitHub
   repositories (D.0), not from new code written in this task.
5. **No upstream reports.** Neither the unrunnable `http_internvla_server.py` nor the `generate_traj` autograd hazard
   is reported to InternNav.
6. **Commit gate:** the path-specific ignore for Phase B/C frames, debug images and arrays is approved and written to
   `.gitignore`. The commit itself still waits for the staged-diff review at E.2.
7. **Model limits are accepted; collision avoidance is required** (2026-09-14). The VLA's navigation judgement (late
   STOP, instruction-independent first answers) is treated as a property of an already large model and is not
   pursued in this task. The safety layer must therefore be model-agnostic: it must protect the robot whatever
   path or command the model produces.

Task activated 2026-09-11; status planning -> in_progress.

## Open decisions for Dr Sun

- Which GPU. The rented 4090 already hosts an Isaac Sim container of unknown ownership; `gpu5070ti` hosts the nav closed loop
  but could not render the NVIDIA Office scene at full materials. The VLA and the renderer may not fit comfortably together.
- Whether to keep ROS 2 Foxy in the loop at all. It exists to host the SCAN planner; if InternVLA-N1 replaces the planner,
  a non-ROS client speaking the bridge's `CMD_VEL_V1` protocol removes the whole Foxy container. See `design.md`.
- Whether Milestone D uses the bare building that is already proven walkable or a furnished scene that is not. A bare
  building cannot support instructions that name objects, so language evaluation needs D even though walking does not.
