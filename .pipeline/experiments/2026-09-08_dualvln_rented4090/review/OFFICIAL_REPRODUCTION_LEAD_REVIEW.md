---
origin: ai+local_evidence+readonly_remote_verification
date: 2026-09-09
reviewer: Codex
status: blocked_with_corrections_required
stage: experiment_and_analysis
---

# Review of the official reproduction return

**No official episode ran.** The blocker report is supported by the returned
logs and a fresh read-only remote check. The evaluation deliverable remains
blocked by missing scene data and an incompatible environment. Additional
launcher/preflight corrections are required; obtaining data alone will not make
the prepared command ready. This review did not install software or run a model.

All paths below are relative to the experiment directory.

## Verified and accepted

- `runs/official_preflight_final/stdout.log` and
  `official_r2r/setup/preflight_report.json` show successful environment-version
  inspection and R2R dataset registration, followed by evaluator import and
  Hydra configuration failures. A diagnostic exit code of zero is not a passed
  evaluator preflight.
- The remote `official_r2r/runs/` directory is empty. The recorded launcher
  refusal is `official_r2r/blocked_attempts/official_subset3_attempt1_20260909T083718Z.txt`.
  No official evaluation process ID, navigation metric, or video can be claimed.
- The remote scene file
  `official_r2r/data/scene_data/mp3d_ce/mp3d/2azQ1b91cZZ/2azQ1b91cZZ.glb`
  is absent. The [official Matterport3D distribution instructions](https://github.com/niessner/Matterport#data)
  require a signed terms form submitted from an institutional email. This review
  verified that access procedure, not a universal claim that no authorized copy
  or distribution could exist elsewhere.
- The original R2R-CE release is linked by the
  [VLN-CE authors](https://github.com/jacobkrantz/VLN-CE#episodes-room-to-room-r2r).
  The local source annotations contain 1,839 episodes. Source SHA-256:
  `d173d8028537f30ab652dc5d24ead737e2b6010b6a4599f974351685710d18e8`.
  Subset SHA-256:
  `ea7ef5bc98904c5885d8a94abe83d6d932137a53a648ebdcbbbbe84e89e4735b`.
  Both match the selection manifest. Episodes 10, 11, and 12 are unchanged
  original objects, and dataset metadata is preserved. All share trajectory 57;
  this is three instruction variants for one route, not three independent routes.
  Preserve the frozen selection and state that limitation.
- The annotation source has not been compared against InternRobotics' gated
  copy. This remains a provenance/parity limitation, distinct from the complete
  absence of an executable scene.
- Independently rehashed all 864 historical observation PNGs and both MP4s
  locally: **866/866 files match**, with zero missing or mismatched files.
  The old episode-observation transfer is complete. This is archival progress
  for the prior custom trials, not a new official navigation result.
- The derived Habitat YAML changes exactly two asset-path lines. The evaluator
  source diff changes only video-saving conditions and output filenames at the
  dual-system and System-2 save sites; no navigation logic change is present in
  that diff. Video output itself has not been exercised by this attempt.

## Required corrections

### O1 — High: actual launcher working directory breaks configuration and asset paths

`official_r2r/scripts/run_official_eval.sh:56` changes directory to
`work/InternNav`, while
`official_r2r/configs/habitat_dual_system_subset3_cfg.py:39` supplies the relative
path `official_r2r/configs/vln_r2r_subset3.yaml`. That file exists relative to the
experiment root, but not relative to the launch directory. Both asset paths
inside the YAML have the same problem.

Fresh remote probes also show the encoder checkpoint exists at the experiment
root's `checkpoints/depth_anything_v2_metric_hypersim_vits.pth`, but not under the
launch directory's `checkpoints/`. The upstream model initializes that auxiliary
encoder from a relative checkpoint path. Resolve all configuration/data/auxiliary
checkpoint paths from a single explicit root, or provide verified task-owned
links while keeping the official entry's required working directory. Do not
alter model math or policy inputs.

`preflight_official.py` changes directory to the experiment root, so its existing
checks do not test the launcher's path resolution. Repeat the config, annotation,
and auxiliary-asset preflight from the actual launch directory after fixing it.

### O2 — High: compatible environment remains an untested candidate

The logs directly establish that the built Habitat-Lab 0.3.3 environment cannot
import `try_cv2_import` or compose the pinned `agents/rgbd_agent` configuration.
They do not establish that Habitat-Lab 0.2.4 will satisfy the whole evaluator.
Treat 0.2.4 as a candidate, not a verified authored-against version.

Building and checking a candidate isolated environment is independent of the
missing MP3D mesh and already within the execution package's scope. Complete
evaluator imports, faithful config composition, and loading the three selected
annotations without waiting for dataset access. Preserve the failed environment
record and document the exact versions/commits used. Do not port navigation
semantics merely to make an incompatible version import.

### O3 — Medium: the documented launcher does not enforce the evaluation budget

The recommended `bash official_r2r/scripts/run_official_eval.sh <run_id>` command
executes Python without a wall-clock supervisor or raw stdout/stderr capture.
The configured step limit is not the package's 1,800-second wall-clock limit.
Use the existing task-owned process-group supervisor, or an equivalent bounded
wrapper, and record command, deadline, logs, and exit status. Verify timeout
handling with a trivial subprocess before any GPU run. A deadline interruption
must remain distinct from completed navigation failure.

### O4 — Medium: readiness reporting must distinguish untested stages

The final preflight's annotation, mesh, and environment-construction stages
all fail again while composing Hydra config. They have not reached their named
checks. Report those stages as blocked by config, and validate mesh existence
independently instead of treating repeated configuration errors as separate
data evidence. This review independently confirmed the missing remote mesh.

The task metadata still says `official_reproduction_dispatch=prepared_not_dispatched`
despite completed preparation jobs and the returned attempt. Record preparation
as executed and official evaluation as not started, preserving the blocked
attempt ID without inventing an evaluation process ID.

## Next execution boundary

Continue environment and launcher repair first, then return a preflight showing
exactly which stages pass without MP3D. Scene access is a separate prerequisite;
the signed access request is not something the executor may submit on the user's
behalf without authorization. An existing authorized asset can also satisfy it.

Once the scene is available and the real launch path passes preflight, execute
the same three frozen episodes under the original package's limits. Keep the
InternRobotics annotation-copy comparison as an explicit open parity issue until
verified. Do not replace official evaluation with another custom scene.

This review adds only this report. Implementation, run artifacts, original
returns, and task metadata are preserved; nothing was staged or committed.
