# Lite3 V12 locomotion loop for InternVLA-N1 (Phase A)

Task: `.trellis/tasks/09-11-internvla-n1-lite3-isaac-sim`. Stage: experiment + analysis.
Label: **reproduced** for the command path, as of run `phase_a_flat_v4` on 2026-09-11. Read `RESULT.md` first.

Phase B (2026-09-14): camera render cost and VLA co-residence, in `RESULT_PHASE_B.md`. Its scripts are
`scripts/phase_b_*`. Result: NO-GO on one 24 GB GPU as specified. After the fallback Dr Sun chose (one-robot PhysX
buffers + `expandable_segments`, with autograd off), it is GO on one GPU for the flat course, with 2.3 GiB headroom.

Phase C (2026-09-14): InternVLA-N1 drives the walking Lite3 through a latency-faithful lockstep, in
`RESULT_PHASE_C.md`. Code is in `phase_c/` and `scripts/phase_c_*`; provenance is in `setup/phase_c_executed_source.json`.
- **Label:** **integrated**, accepted after an independent review at C.5.
- **Outcome over six episodes:** success 0/6, oracle 1/6, no falls.
- **Failures:**
  - the model said STOP after passing the target sideways, with the target out of view;
  - one body-clearance collision.

Phase D (2026-09-14, in progress): body-clearance margin, in `RESULT_PHASE_D.md`. D.0a offline footprint clearance
done. D.0c scripted tests done (integrated, not validated): unmodified Nav2 `collision_monitor` in the Isaac loop removed
the replayed green-episode contact, halted head-on and corner approaches about 0.10 m short, and stopped on a stale
cloud. D.0d (3 InternVLA-N1 episodes with the monitor): success 0/3, oracle 1/3, no contact, and the monitor changed
0 of 1,092 commands because the model never drove at a box. D.0e (goal behind a box, 3 episodes): the model swung
right away from both boxes every time (identical first pixel goal), 60 s timeouts, 0 commands changed, no contact.
D.0f (the real two-camera fusion in Isaac, built-in camera +16.7° and URDF D435i −20° fused into the c8 view): three preflights (two refused on camera geometry, the third passed the c8-bound gate with a bit-exact recompute), then green/red/blue VLA episodes with every received frame inside the c8 bounds; success 0/3, oracle 0/3 (ideal D.0d 1/3), late STOPs 5-12 m past the target, 0 commands changed, no contact. D.0g (offline, no GPU): in the 42 of 148 System 2 pixel-goal answers with the target box in view, none put the goal on the box (median bearing error 25.1°), so the coordinate is a route waypoint, not a target location.

## What Phase A is for

Milestone A, AC1–AC2: get the V12 locomotion loop into our own hands and prove the command path, before any camera
(Phase B) or any VLA (Phase C) is involved. The proof is narrow and mechanical: a commanded body-frame velocity
`(vx, vy, wz)` must appear **unchanged** in the policy's own 450-dimensional observation, at command-history offset 60.
The adapter's `_policy_command_evidence()` does exactly that check and raises if the error exceeds 1e-6.

No training. No optimiser. No checkpoint is written. No camera is enabled — `enable_cameras` stays `False` until
Phase B, which is the render-cost go/no-go for the whole task.

## The run

`--mode qualification --course flat`, which drives the built-in `DEFAULT_QUALIFICATION_SCHEDULE`
(`isaac_adapter_core.py:28`), 8.75 simulated seconds:

| segment | seconds | (vx, vy, wz) |
| --- | --- | --- |
| settle_zero | 1.0 | 0, 0, 0 |
| forward | 2.0 | 0.30, 0, 0 |
| lateral | 2.0 | 0, 0.18, 0 |
| yaw | 2.0 | 0, 0, 0.40 |
| stop_zero | 1.0 | 0, 0, 0 |
| watchdog_disconnect | 0.75 | 0, 0, 0 (client disconnected) |

It exercises each command axis on its own and then the 250 ms watchdog — the whole command contract in nine seconds.

## Inputs, and where their authority comes from

`setup/inputs.json` pins all three and records how each was verified.

- `references/upstream/2026-09-11_lite3_sim_bridge/` — 15 files, **tracked in git**. Vendored from an uncommitted
  `machine-dog-nav` working tree; the authority is the accepted run `native_full02`'s executed-source manifest, not a
  commit. `run_isaac_v12_fallback.py` hashes to `6104fe68…` — the exact module that run loaded.
- `references/upstream/2026-09-11_lite3_v12_locomotion/` — 218 files, 111 MB, local-only under a reviewed ignore with
  tracked `SOURCE.md` + `SHA256SUMS.txt`. machine-dog commit `8c3fdffa` for identity; bytes from the recovered runtime
  tree, because that commit's allow-list cannot export them.
- `model_149999.pt`, 26,367,345 bytes, `a9d31dce…3d5450`. The adapter fails closed on a mismatch.

## Scripts

    python3 scripts/build_bundle.py --verify-only   # re-verify both pinned trees, pack nothing
    python3 scripts/build_bundle.py                 # -> setup/bundle/phase_a_bundle.tar.gz + bundle_manifest.json
    scripts/phase_a_stage.sh SSH_TARGET [ROOT]      # upload, compare SHA-256 on the host, extract, re-verify
    scripts/phase_a_run_native.sh RUN_ID [SECONDS]  # runs ON a native conda Isaac Lab host

`build_bundle.py` verifies both `SHA256SUMS.txt` files before packing, so a divergent local tree cannot be shipped,
and writes deterministic tar metadata so the archive hash depends on content rather than the build clock.
`phase_a_run_native.sh` refuses to overwrite an existing run directory, refuses to collide on a port, and **reports**
a stale runner by pid rather than killing it — the execution hosts carry other people's work.

## Execution host: the rented 4090 (Dr Sun, 2026-09-11)

`setup/host_survey.json` holds the read-only survey and its correction. The first version of that survey said the
4090 could not run this because `isaaclab_tasks` and `isaaclab_rl` were absent. That was wrong: the PyPI `isaaclab`
2.3.2.post1 wheel bundles the entire IsaacLab source tree at `site-packages/isaaclab/source/`, and `find_spec`
returned `None` only because those roots are not on `sys.path`. Four `PYTHONPATH` entries, no download, no image
rebuild, no version mixing.

`gpu5070ti` is kept in the survey as the control: the accepted 74 m V12 run executed there with byte-identical bridge
source, so a future 4090 failure can be isolated to the environment rather than the code.

    python3 scripts/probe_sink_defect.py                          # reproduces the upstream sink bug, stdlib only
    VLA_SSH_OPTS="-J gpu40901" scripts/phase_a_stage.sh rented4090
    #   then ON the host: bash phase_a_run_docker.sh RUN_ID 12
    VLA_SSH_OPTS="-J gpu40901" scripts/collect_run.sh rented4090 RUN_ID

## Claim boundary

Staging and verification are not a run. Until `runs/<run_id>/` holds an adapter exit code, a
`runtime_import_identity.json` proving which source the interpreter loaded, and the command-evidence record, Phase A
claims nothing about whether the loop works here.
