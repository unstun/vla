# v283 execution and recovery record

The local VLA checkout is the source of truth. All remote source is an execution
copy. No frozen file may change after the recorded identities below.

Native manifest SHA256:
`caeea41b0dbb99ca10ae74b1cf6239535d4c2c4d25327f53988d8afe7b1393f4`.
Execution manifest SHA256:
`8d22f7e0ebeb90432b6811462d95dd175613bb3e4902d5b4634fe6b0ca38cc71`.

## Paths and ordered execution

Host: gpu5070ti. Remote experiment directory:
`/data/sun/vla_mppi_20261009/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction`.
Private Python: `/home/sun/vla_exec/envs/newton_worker/bin/python`.
Native/cohort/offline root: `/home/sun/vla_exec/navigation_geometry_v283`.
Physical root: `/home/sun/vla_exec/physical_runs_v283`.
Compact execution receipts: `/data/sun/vla_mppi_20261009/generalization_v283`.

Under the remote experiment directory, the versioned entry points are:

```sh
python3 versions/v283/prepare.py
python3 versions/v283/build.py
python3 versions/v283/regressions.py
python3 versions/v283/construct_starts.py
/home/sun/vla_exec/envs/newton_worker/bin/python versions/v283/capture_cases.py
python3 versions/v283/freeze_native.py
python3 versions/v283/run_matrix.py
python3 versions/v283/prepare_execution.py
/home/sun/vla_exec/envs/newton_worker/bin/python audits/2026-10-19_v283_navigation_geometry/run_preflights.py
python3 versions/v283/freeze_execution.py
```

Native build/contract/readiness logs and the full offline ledger are already
complete. These commands document the entry points; do not repeat the scored
matrix or overwrite freezes. All ten zero-physics preflights passed invocation01.

## Storage recovery and failed launches

The first physical dispatcher rejected A04/G05/CU06/D07/S04 before simulator
construction at the inherited `/data` free-space gate. The initial dispatcher
incorrectly inferred physical start from an early launch ledger. Preserve that
status; use direct runtime traces to classify five zero-physics launch rejections
outside the physical denominator. Each raw entry has only six initialization
files and an approximately0.03s process ending with the disk-gate traceback.

Audit `relocate_archive.py` moved the inactive5.29GB `mac_archive_20261012` to
`/home/sun/vla_exec/relocated_archives/`, verifying SHA256 and mode of every entry
before freeing the redundant original. The original path remains a symlink.
Audit `archive_launch_failures.py` preserved complete failed task directories at
`physical_runs_v283/launch_failures01/` and execution receipts at each case's
`execution_launch_failure01`. Local compact inventories/logs are in
`audits/2026-10-19_v283_navigation_geometry/results/recovery/`.

No frozen code, profile,0.35m radius,0.1s period/deadline, or disk threshold changed.

## Frozen ten-route batch

After the recovery, a detached owned process runs:

```sh
/home/sun/vla_exec/envs/newton_worker/bin/python audits/2026-10-19_v283_navigation_geometry/execute_batch.py
```

Coordinator receipt/log: private root `physical02_coordinator.json` and
`physical02.log`. The dispatcher holds `results/physical_batch.lock`; resume only
unattempted cases using its explicit status/ledger checks. It checks the
unchanged20GiB available RAM, idle GPU and10GiB output free-space gates. Do not
start another batch while the owned coordinator is active. Each frozen launch
also checks source identity and the inherited disk gate.

Order: A04, G05, CU06, D07, S04, CD12, CM02, CM07, CS03, CE03. G05 and CM02 use
the uniformly certified replacement starts. Exactly one actual physical attempt
per route; preserve any failed outcome without a success-seeking retry.

After all physics processes close:

```sh
/home/sun/vla_exec/envs/newton_worker/bin/python audits/2026-10-19_v283_navigation_geometry/postprocess_all.py
python3 audits/2026-10-19_v283_navigation_geometry/collect_physical.py
```

Return only `physical_return/`, `delivered/*.mp4`, compact batch/resource/recovery
receipts, and review frames. Verify returned inventory hashes, full video decode,
state coverage, and visually inspect every route. Then run locally:

```sh
python3 audits/2026-10-19_v283_navigation_geometry/summarize_physical.py
```

All analysis/rendering operates on recorded states with zero new physics. Full
raw captures, archives, builds and environments remain remote. A video or a
process exit alone does not establish arrival, PD or geometry acceptance.

## Supplemental closed-recording diagnosis

`audits/2026-10-19_v283_navigation_geometry/failure_bill.py` extracts actual
planner, controller and mission terminal errors; its first extraction is
preserved separately. `diagnose_recording.py` reconstructs published D07/S04
curve poses at the first/worst solid excursions and queries the unchanged exact
field. `witness_controls.py` binds those poses to actual applied telemetry and
the pinned tracker/controller source. Use the private Newton Python; outputs
are in the private root's `candidate_diagnostics/` and return locally to
audit `results/candidate_recording/`. Preserve existing derived results before
regenerating them. None of these tools starts physics.

Reconstructed phase uses published epoch plus elapsed time. The actual tracker
can freeze phase during heading control, so this is not an exact tracker replay.
Commands and physical body poses come directly from immutable capture records.

## Recorded-state rendering admission

All ten physical attempts used the unchanged20GiB available-RAM / idle-GPU /
10GiB output-disk gate. The original analysis dispatcher unnecessarily reused
that physical gate for rendering and waited after six complete videos when a
foreign GPU evaluation started. Its six results/log and transition receipt are
retained. No case writer was active when the owned waiting dispatcher was stopped.

`after_physics.py` with `V283_ANALYSIS_ID=02` resumes only closed recordings and
skips already hash-verified videos. Its log/receipt are private-root `analysis02.log`
and `after_physics02.json`. `render_resources.py` requires all ten physical cases
closed, >=8GiB available RAM, >=2GiB free GPU memory and >=10GiB output disk;
it permits GPU sharing for this zero-physics work only. Case postprocessing runs
at nice10 with the existing single-thread BLAS/OpenMP settings. Resource probes
and observed peer GPU use are saved in audit results. The frozen physical gate
and all numerical/profile/source identities remain unchanged.

## CM07 camera-only review revision

Local review found the original CM07 terminal camera hidden by a pillar.
`repair_camera.py` calls only the existing recorded-state `render()` path, with
the generic `V283_RENDER_CAMERA=close_body` mode and `V283_RENDER_ID=03`.
Trail/height/ahead/down are0.35/0.50/0/0.05m, yaw smoothing0.2s, FOV95degrees.
Scene meshes, recorded poses, timestamps, overlays, outcome and physics remain
unchanged. The wider FOV retains the entire robot and legs.

Camera01 and intermediate02 master videos/source snapshots are preserved on the
remote host. Revision verification proves identical2951source indices/times and
physical input hashes for01 versus03. Final local stream/hash and startup/middle/
terminal visual checks use03; there is still exactly one physical CM07 attempt.
