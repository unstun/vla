---
origin: ai+local_inspection
reviewed: false
date: 2026-09-09
status: prepared_not_dispatched
package_version: 2-corrections
lead: Claude Fable 5.1
executor: Opus (manual dispatch by Dr Sun)
depends_on: OPUS_EXECUTION_PACKAGE.md (v2), OPUS_RETURN.md (round 1), review/LEAD_REVIEW_2026-09-09.md
---

# LightNav-0 official demo: correction package (round 2)

Read `AGENTS.md`, then `review/LEAD_REVIEW_2026-09-09.md` (the findings you are
correcting), then this file. The original package still governs everything not
restated here: same case, instruction, model settings, controller, boundaries,
supervisor, sync gate, and the ban on staging or committing. Write in English.

## Goal and scope

- Goal: complete the contracted deliverables, repair the task-owned recorder, add
  three recorder-complete repetitions, and return a corrected report with an honest
  task-outcome assessment.
- Owned paths: `EXP` and the task directory, as before. Keep every existing file
  under `runs/rep_01..03`, `records/`, `runs/*/` and `review/` byte-for-byte; add, never
  overwrite. The lead's `review/` files are read-only inputs.
- Remote: `REMOTE` as before; `env/`, `checkpoints/`, `work/` are still in place and
  verified; do not rebuild them.
- Budget: model startup plus all new navigation attempts at most 900 s of GPU time;
  everything else at most 90 min wall time. Report overruns as deviations.

## Corrections

1. **Repair `scripts/run_episode.py`** (task-owned harness; upstream code untouched):
   - name frames with a monotonic per-stream counter, never from a file offset;
   - keep `received_utc` per frame and add the poll's monotonic time and the snapshot
     `simulation.camera.stamp_ns` and `sim_time` closest to it;
   - compute the post-stop check explicitly: after `vln.stop == true` and
     `control.source == idle`, require 2.0 s of snapshots with zero `command` and an
     unchanged pose, and write the result to `episode.json`;
   - label the termination cause as one of `model_stop | invalid_output | disconnect |
     mpc_error | watchdog_timeout | decision_cap | harness_stop`, treating a
     non-empty `mpc.error` or `vln.state == ERROR` persisting more than 5 s as a
     failure, and record the harness-sent `set_vln enabled:false` when it happens;
   - measure `wall_seconds` from the `set_vln` send, and keep the pre-start reset time
     as a separate field.
   Run the harness against a fresh demo session for a dry run of at most 15 s with
   `enabled:false` sent by the harness, and keep that run as `runs/harness_check`.

2. **Run three additional repetitions `rep_04`, `rep_05`, `rep_06`** with the repaired
   harness: restart the model server and the demo exactly as in round 1 (same launch
   scripts; a new `records/run_*` directory will appear), same reset-then-start
   procedure, same limits. These are not retries for success; they exist because the
   round-1 third-person raw evidence is incomplete. Report both sets; do not merge them
   into one statistic without labels.

3. **Videos for all six runs** (`scripts/make_videos.py`, decode-checked):
   - first-person overlay via `lightnav-render` on each run's server episode directory
     (round-1 files already exist; do not overwrite them);
   - third-person MP4 from the recorder frames using their timestamps (10 fps constant
     with duplication, or VFR via ffmpeg concat); for rep_01-03 use the surviving files
     and state the gaps from the index rows that name overwritten files;
   - paired side-by-side MP4 with wall-clock and decision-index labels;
   - per video: frame count, distinct-frame count, size, SHA-256; save start, mid and
     terminal PNGs and look at them.

4. **Analysis** (`scripts/analyze.py` -> `analysis/summary.json` and `analysis/summary.md`)
   per run: decisions; latency mean/max from `actions.json`; MPC `solve_ms` stats from
   snapshots; path length, displacement, terminal pose; planar distance and
   (ahead, right) components to `ashcan_c6c85e44c01b199881223a6a35b693a4_1_0_4` at
   (8.52, 9.36) and to `pad_40f0405be70264b3ffe8b32e9347537b_1_0_4` at (9.82, 10.41),
   computed from `val_2_ceiling.xml` as in `review/lead_terminal_geometry.json`;
   `opos_state`/`opos_px` and `visible` at the stop step and the visible fraction;
   termination cause with the snapshot index of the transition and the computed
   post-stop check; GPU peak from the sampler; first step at which each run's
   `raw_text` diverges from rep_01. Then a qualitative arrival statement per run:
   which object the robot stopped in front of, and whether the instructed trashcan
   was reached. Report failures as failures.

5. **Case and environment records**: augment `runs/case.json` (keep the raw health
   response under a `health` key) with instruction text and SHA-256, spawn, camera
   geometry, checkpoint manifest SHA-256, resolved eval config, decode settings,
   versions, launch commands, and the two object positions above. Write
   `setup/environment.json` (versions JSON, `nvidia-smi -q` summary, and the SHA-256 of
   the `torch`, `vllm`, `transformers`, `nvidia-cutlass-dsl` wheels from `env/uv_cache`
   compared with PyPI's published digests).

6. **Failed-attempt evidence**: describe the two round-1 failed harness attempts in the
   return and point to `records/run_20260909_235443/vln_mujoco/episode_000`; never
   delete run directories again.

7. **Return**: copy the round-1 report to `review/OPUS_RETURN_round1.md` unchanged,
   then write a corrected `OPUS_RETURN.md` (round 2) that fixes the local-checkpoint
   statement, includes the six-run table and the arrival assessment, and lists every
   deviation. Return the new remote files with one tar archive, write
   `return_manifest.json` (relative path, bytes, SHA-256 for every file under `runs/`,
   `records/`, `analysis/`, `scripts/`, `setup/` except the lead's files) after all files
   are final, verify every local byte against it, and write the result to the separate
   `return_verification.json`. Stop your services by PGID, confirm PID 1247 unchanged,
   set the task meta `execution_status=review`, and do not stage or commit.

## Acceptance for this round

| Check | Pass condition |
|---|---|
| Recorder | for rep_04-06, index rows == files on disk == polled frames for both streams |
| Six runs | each `episode.json` has a termination label, the explicit post-stop check, and a matched server episode directory |
| Media | 6 first-person, 6 third-person, 6 paired MP4s decode; PNGs saved; gaps for rep_01-03 stated |
| Analysis | `analysis/summary.json` has every field above for all six runs, with the arrival statement |
| Report | `OPUS_RETURN.md` round 2 corrects the checkpoint statement and matches the analysis |
| Manifests | `return_manifest.json` verified with 0 mismatches; `review/OPUS_RETURN_round1.md` identical to the round-1 report |
| Boundaries | no upstream source change (or a `setup/compatibility.patch` with justification), PID 1247 unchanged, nothing staged |

The lead will re-verify the new snapshots, records, videos and manifests before
accepting the task.
