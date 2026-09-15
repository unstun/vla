---
origin: ai+remote_execution_evidence
date: 2026-09-10
executor: Opus (background subagent of the lead session)
lead: Claude Fable 5.1
status: partial_execution_lead_decision_required
trellis_task: .trellis/tasks/09-10-internvla-n1-camera-ablation-sim
package: OPUS_EXECUTION_PACKAGE.md
---

# Opus return: Lite3 camera-condition ablation of InternVLA-N1 DualVLN

**Headline.** Preflight passed for C3 and C4 and failed for C1 and C2 on the
floor z-depth sub-check only. Ten supervised evaluator runs (C3 and C4, five
each) completed with exit 0 and no timeouts; C1 and C2 were **not run** and are
held for a lead decision, exactly as the package requires. All evidence is back
at the local paths and the local manifest verifies 787/787.

Nothing was staged or committed. No model, evaluator, condition, protocol, or
acceptance criterion was changed. No process that the executor did not start was
stopped or touched; the resident `isaac-sim` container ran throughout.

Paths are relative to
`/Users/sun/tongbu/study/phdproject/vla/.pipeline/experiments/2026-09-08_dualvln_rented4090`
(`EXP`). `REQ` = `EXP/public_scenes/requests/2026-09-10_lite3_camera_ablation`.
Remote execution copy:
`/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090` on `rented4090`.

## 1. Sync Gate in (package step 1) — PASSED

```bash
# local, from EXP
rsync -av --exclude '.DS_Store' --exclude '._*' \
  public_scenes/requests/2026-09-10_lite3_camera_ablation/ \
  rented4090:/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090/public_scenes/requests/2026-09-10_lite3_camera_ablation/
rsync -av --exclude '._*' \
  public_scenes/configs/vln_cam_c1_lite3_rig.yaml \
  public_scenes/configs/vln_cam_c2_height_only.yaml \
  public_scenes/configs/vln_cam_c3_fov_only.yaml \
  public_scenes/configs/vln_cam_c4_raised_mount.yaml \
  public_scenes/configs/habitat_dual_system_cam_cfg.py \
  rented4090:/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090/public_scenes/configs/

# remote, from the EXP root
sha256sum -c public_scenes/requests/2026-09-10_lite3_camera_ablation/authored_files.sha256
sha256sum work/InternNav/internnav/habitat_extensions/vln/habitat_vln_evaluator.py
```

- `authored_files.sha256`: **15 of 15 lines OK**, exit 0.
- Remote worktree evaluator hash:
  `a05268d5e4fac8ab6147d2c828e16ae76d413fe074d2e7f0f99e26ae6fcbf3e7` —
  **equal to the pinned baseline value**.
- Before the sync the remote held no `cam_*` run directory and no
  `2026-09-10_lite3_camera_ablation` request directory, so no run id was reused.

## 2. Resource check (package step 2) — PASSED, no waiting needed

Recorded in `REQ/preflight/resources_before.txt` (2026-09-10T09:42:37Z).

| Item | Value |
| --- | --- |
| Device | NVIDIA GeForce RTX 4090, 24,564 MiB, driver 575.57.08, CUDA 12.9 |
| Used before the matrix | 2,903 MiB |
| **Free before the matrix** | **21,179 MiB** |
| Resident GPU process | PID 1251 `/isaac-sim/kit/kit`, 2,859 MiB, untouched |
| Host | 62 GB RAM, 43 GB free on `/` (10 runs consumed about 0.5 GB) |

Free memory (21,179 MiB) exceeded the baseline footprint of about 19.5 GB on
the first sample, so the 5-minute polling branch was not entered. Observed peak
device memory during the matrix was **22,385 MiB** across all runs, i.e. an
evaluator footprint of about 19,482 MiB on top of the resident Isaac Sim.

## 3. Preflight (package step 3) — 2 of 4 PASSED

```bash
cd /home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
bash public_scenes/scripts/link_launch_dir.sh
cd work/InternNav
mkdir -p public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight
for c in c1_lite3_rig c2_height_only c3_fov_only c4_raised_mount; do
  CAM_YAML=public_scenes/configs/vln_cam_$c.yaml \
    ../../official_r2r/official_env_024/bin/python \
    public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight_cam.py --cond $c \
    2>&1 | tee public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight/${c}_stdout.txt
done
```

Run unattended through `REQ/preflight/run_preflight_all.sh` (see Deviation D1).
`link_launch_dir.sh` reported `LAUNCH_LINKS_DONE` with all seven paths OK
(`REQ/preflight/link_launch_dir.txt`).

### 3.1 Result per condition

| Cond | Stages 1–5 | Sensor height (measured / spec) | Pitch down (measured / spec) | Forward offset (measured / spec) | Floor z-depth p90 measured / expected | Deviation | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C1 `c1_lite3_rig` | all PASS | 0.4200 / 0.42 m | 20.000 / 20 deg | 0.2500 / 0.25 m | 0.850 / 0.618 m | **+37.5 %** | **FAIL** (floor sub-check only) |
| C2 `c2_height_only` | all PASS | 0.4200 / 0.42 m | 0.000 / 0 deg | 0.2500 / 0.25 m | 0.996 / 0.723 m | **+37.8 %** | **FAIL** (floor sub-check only) |
| C3 `c3_fov_only` | all PASS | 1.2500 / 1.25 m | -0.000 / 0 deg | -0.0000 / 0.0 m | 3.936 / 3.481 m | +13.1 % | **ALL_STAGES_PASSED** |
| C4 `c4_raised_mount` | all PASS | 0.6500 / 0.65 m | 15.000 / 15 deg | 0.2500 / 0.25 m | 1.335 / 1.073 m | +24.4 % | **ALL_STAGES_PASSED** |

C3 and C4 each printed `ALL_STAGES_PASSED` and wrote
`preflight/<cond>.json` with `all_stages_passed: true`, including stage 6
(`look_down/look_up behave per tilt_angle`, so `tilt_angle: 0` is confirmed a
no-op) and stage 7 (`GPU budget against the baseline footprint`).

Composed-config stage 5 passed for **all four** conditions: resolved
`position`, `orientation`, `hfov`, and `tilt_angle` for both RGB and depth
sensors equal `conditions.json` exactly, at 640x480, `depth_min_max [0, 10]`,
`agent_height 1.5`, `agent_radius 0.1`, `forward_step_size 0.25`,
`turn_angle 15`.

Eight PNGs were written; all four RGB and all four depth PNGs exist and are
returned for lead inspection (`REQ/preflight/<cond>_start_rgb.png`,
`<cond>_start_depth_mm.png`).

### 3.2 C1 and C2: exactly what failed

Both raised the same single-item error from `preflight_cam.py:303`:

```
RuntimeError: render check failed: bottom-row floor z-depth 0.850 m vs expected 0.618 m   # C1
RuntimeError: render check failed: bottom-row floor z-depth 0.996 m vs expected 0.723 m   # C2
```

`preflight_cam.py` appends the sensor-height, pitch-sign, and forward-offset
violations to the **same** `problems` list as the floor sub-check (lines
296-303). Only the floor item appears, so for both conditions the measured
sensor height was within 0.01 m, the pitch within 0.5 deg, and the forward
offset within 0.01 m of the specification. **The orientation sign convention is
therefore confirmed correct for C1 as well** (negative x orientation = pitched
down): the simulator's own sensor state at the episode-1 reset gives, from
`REQ/preflight/c1_lite3_rig_stdout.txt`, sensor position y = 0.53083885 against
agent y = 0.11083889 (height 0.42000) and sensor rotation
`quaternion(0.984807729721069, -0.173648178577423, ...)` = 20.000 deg down;
C2's stdout gives the same height with an identity rotation (0.000 deg).

The stage raised before returning its `detail` dict, so
`c1_lite3_rig.json` and `c2_height_only.json` carry the traceback rather than
the numbers; the values above are read back from the two stdout logs, which are
returned.

### 3.3 Observation offered to the lead, not acted on

The four measurements are internally consistent with a single systematic bias in
the *expectation*, not with an error in any condition's geometry. Writing
`r = measured / expected`:

| Cond | Height h | Pitch | r | Implied floor offset `h*(r-1)` |
| --- | --- | --- | --- | --- |
| C1 | 0.42 m | 20 deg | 1.3754 | 0.1577 m |
| C2 | 0.42 m | 0 deg | 1.3776 | 0.1586 m |
| C3 | 1.25 m | 0 deg | 1.1307 | 0.1634 m |
| C4 | 0.65 m | 15 deg | 1.2442 | 0.1587 m |

A single constant of about 0.16 m — the vertical gap between the agent origin
(the navmesh point the episode starts on) and the actual floor mesh — reproduces
all four measurements to within 0.4 percent, across three camera heights, three
pitches, and both fields of view:

| Cond | Expected with a 0.16 m floor gap | Measured | Residual |
| --- | --- | --- | --- |
| C1 | 0.853 m | 0.850 m | -0.4 % |
| C2 | 0.998 m | 0.996 m | -0.2 % |
| C3 | 3.927 m | 3.936 m | +0.2 % |
| C4 | 1.337 m | 1.335 m | -0.2 % |

The preflight builds its expectation from `spec['height_m']`, the sensor height
above the **agent origin**, and so implicitly assumes the agent origin lies on
the floor. The relative bias is `1 + 0.16/h`, which is +12.8 % at 1.25 m,
+24.6 % at 0.65 m, and +38.1 % at 0.42 m — larger than the 25 percent tolerance
only for the two 0.42 m conditions. On the same reading C4 passed with 0.6
percentage points of margin, so its pass is not strong independent evidence
either.

This is an interpretation of returned numbers, **not a verified root cause**: it
was not confirmed against the scene mesh, and no fifth preflight was run. It
would change the preflight's acceptance criterion, which is outside the
executor's scope, so nothing was altered. **The lead decides.**

## 4. Matrix (package step 4) — 10 of 20 runs, all exit 0

```bash
cd /home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
bash public_scenes/requests/2026-09-10_lite3_camera_ablation/run_matrix.sh \
  c3_fov_only c4_raised_mount 2>&1 | tee -a public_scenes/requests/2026-09-10_lite3_camera_ablation/matrix_stdout.txt
```

Conditions were named explicitly (see Deviation D2) because `run_matrix.sh`
gates only on the *existence* of `preflight/<cond>.json`, not on its verdict.
C1 and C2 have a report file that records failure, so an unqualified invocation
would have launched them, `run_cam_eval.sh` would have refused each with exit 5,
and ten run ids would have been permanently consumed by refusals.

`REQ/matrix_log.jsonl`, all 10 lines:

| Run id | Condition | exit_code | timed_out | wall s |
| --- | --- | --- | --- | --- |
| cam_c3_fov_only_v1 | c3_fov_only | 0 | false | 229.0 |
| cam_c3_fov_only_v2 | c3_fov_only | 0 | false | 308.4 |
| cam_c3_fov_only_v3 | c3_fov_only | 0 | false | 139.0 |
| cam_c3_fov_only_v4 | c3_fov_only | 0 | false | 173.8 |
| cam_c3_fov_only_v5 | c3_fov_only | 0 | false | 132.1 |
| cam_c4_raised_mount_v1 | c4_raised_mount | 0 | false | 276.5 |
| cam_c4_raised_mount_v2 | c4_raised_mount | 0 | false | 210.2 |
| cam_c4_raised_mount_v3 | c4_raised_mount | 0 | false | 212.2 |
| cam_c4_raised_mount_v4 | c4_raised_mount | 0 | false | 180.4 |
| cam_c4_raised_mount_v5 | c4_raised_mount | 0 | false | 217.6 |

- **20 of 20 runs authorized were not used: 10 launched, 10 completed.**
- Every run: `exit_code` 0, `timed_out` false, well inside the 1,800 s deadline
  (max 308.4 s). Total matrix wall time about 34 minutes.
- Ten directories `public_scenes/runs/cam_*` each hold `progress.json` with
  **two** episode records (verified: 10 of 10), plus `inputs.json`,
  `result.json`, `trace_0/`, `vis_0/`, `vis_debug/`, `environment.json`,
  `gpu_samples_every_5s.csv`, `exit.json`.
- Ten supervisor records `runs/cam_*` with `meta.json`, `stdout.log`,
  `stderr.log`, `process.json`.
- No CUDA out-of-memory occurred; the OOM stop rule was never triggered.
- No run was deleted or rerun under an existing id.

Input identity, cross-checked by the executor against
`public_scenes/runs/public_eval_v5/inputs.json`: all 10 runs record byte-identical
SHA-256 for `scripts/eval/eval.py`,
`internnav/habitat_extensions/vln/habitat_vln_evaluator.py`,
`internnav/model/utils/vln_utils.py`, `skokloster-castle.glb`,
`skokloster-castle.navmesh`, and the frozen annotation `val_unseen.json.gz`
(0 mismatches). The eval config and the Habitat YAML differ from the baseline by
design.

## 5. Summary and media checks (package step 5) — PASSED

```bash
official_r2r/official_env_024/bin/python \
  public_scenes/requests/2026-09-10_lite3_camera_ablation/summarise_conditions.py
PATH=/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090/official_r2r/official_env_024/bin:$PATH \
  python3 <the package's ffprobe block>
```

`ffprobe` is not on the remote default PATH; it ships inside the pinned
environment at `official_r2r/official_env_024/bin/ffprobe` (version 8.0), which
was prepended to PATH. See Deviation D3.

- **B0 gate: the summariser reproduced the recorded baseline exactly — episode 1
  3/5, episode 2 2/5** — matching `EXP/review/PUBLIC_SCENES_LEAD_REVIEW.md`
  before any new condition is reported.
- **40 MP4s probed, 0 decode errors.**
- **20 of 20 `vis_debug` videos have a frame count exactly equal to `steps` in
  `progress.json`** for the matching episode; 20 `vis_0` top-down videos also
  decode cleanly.

### `condition_summary.md`

| Condition | Height | Pitch | HFOV | Tilt | Ep1 success | Ep1 NE m (min/med/max) | Ep2 success | Ep2 NE m (min/med/max) | Ep2 collisions (min/med/max) | Learned STOP | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 baseline (recorded) | 1.25 m | 0 deg | 79 | 15 | 3/5 | 1.05/1.252/4.057 | 2/5 | 2.154/4.892/5.911 | 8/10/10 | 10/10 | 5/10 |
| c1_lite3_rig (Lite3 rig faithful) | 0.42 m | 20 deg | 54 | 0 | 0/0 | - | 0/0 | - | - | 0/0 | 0/0 |
| c2_height_only (Height only) | 0.42 m | 0 deg | 79 | 15 | 0/0 | - | 0/0 | - | - | 0/0 | 0/0 |
| c3_fov_only (FOV only) | 1.25 m | 0 deg | 54 | 15 | 2/5 | 1.208/13.877/16.3 | 1/5 | 2.488/5.424/9.045 | 2/4/4 | 10/10 | 3/10 |
| c4_raised_mount (Raised mount candidate) | 0.65 m | 15 deg | 54 | 0 | 2/5 | 0.785/14.45/16.901 | 0/5 | 4.505/8.931/10.202 | 17/40/58 | 10/10 | 2/10 |

The `0/0` rows for C1 and C2 mean "no runs recorded", not a zero score.

Supporting detail from `condition_summary.json` (executor transcription; the
lead recomputes from `progress.json` and the traces per AC4):

| Condition / episode | Success | Oracle success | Entered radius | Learned STOP | Steps min/med/max | Collisions min/med/max | S2 level_view / look_down_followup | Pixel goals min/med/max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 ep1 | 3/5 | 3 | 3 | 5/5 | 63/80/81 | 0/0/0 | 53 / 37 | 6/8/8 |
| B0 ep2 | 2/5 | 5 | 5 | 5/5 | 86/107/116 | 8/10/10 | 66 / 55 | 9/12/12 |
| C3 ep1 | 2/5 | 2 | 2 | 5/5 | 76/107/364 | 1/2/49 | 112 / 77 | 7/10/38 |
| C3 ep2 | 1/5 | 3 | 3 | 5/5 | 67/100/102 | 2/4/4 | 60 / 49 | 7/11/11 |
| C4 ep1 | 2/5 | 3 | 3 | 5/5 | 80/99/145 | 0/3/6 | 73 / 54 | 8/10/15 |
| C4 ep2 | **0/5** | **0** | **0** | 5/5 | 160/218/269 | 17/40/58 | 144 / 108 | 17/21/27 |

All 20 new episodes ended on a learned System-2 STOP; none hit the 500-step cap
or the deadline. The two observations most likely to matter to the lead's
reading, stated descriptively: C4 episode 2 never entered the goal radius in any
of five runs (B0 entered in 5 of 5) while accumulating 17 to 58 collisions and
160 to 269 steps; and C3 episode 1 shows a bimodal navigation error, 1.208 m in
the successful runs against 13.9 to 16.3 m otherwise. Attribution to System 1 or
System 2 is outside this test's claim boundary.

## 6. Manifest and Sync Gate out (package step 6) — PASSED

```bash
# remote, from the EXP root, after the last evidence edit
find public_scenes/runs/cam_* runs/cam_* public_scenes/requests/2026-09-10_lite3_camera_ablation -type f \
  ! -name manifest.sha256 ! -name OPUS_RETURN.md -print0 | sort -z | xargs -0 sha256sum \
  > public_scenes/requests/2026-09-10_lite3_camera_ablation/manifest.sha256

# local, from the EXP root
rsync -a "rented4090:.../public_scenes/runs/cam_*" public_scenes/runs/
rsync -a "rented4090:.../runs/cam_*" runs/
rsync -a rented4090:.../public_scenes/requests/2026-09-10_lite3_camera_ablation/ \
         public_scenes/requests/2026-09-10_lite3_camera_ablation/
shasum -a 256 -c public_scenes/requests/2026-09-10_lite3_camera_ablation/manifest.sha256
```

- Manifest: **787 files**, verified remotely (0 non-OK lines).
- **Local verification: 787 of 787 lines OK, exit 0.** Full output kept at the
  executor's scratchpad; the manifest itself is the returned artifact.
- About 552 MiB (578,804,350 bytes) of run evidence transferred.

Returned local paths (all under `EXP`):

- `public_scenes/runs/cam_c3_fov_only_v{1..5}/`
- `public_scenes/runs/cam_c4_raised_mount_v{1..5}/`
- `runs/cam_c3_fov_only_v{1..5}/`
- `runs/cam_c4_raised_mount_v{1..5}/`
- `public_scenes/requests/2026-09-10_lite3_camera_ablation/` in full, including
  `preflight/` (4 JSON reports, 8 PNGs, 4 stdout logs, `link_launch_dir.txt`,
  `preflight_all_stdout.txt`, `resources_before.txt`), `matrix_log.jsonl`,
  `matrix_stdout.txt`, `matrix_driver_stdout.txt`, `condition_summary.json`,
  `condition_summary.md`, `ffprobe_frame_counts.json`, `manifest.sha256`, and
  this `OPUS_RETURN.md`.

The remote copy retains the identical files; `OPUS_RETURN.md` was copied to the
remote `REQ` after the manifest was generated and is deliberately excluded from
it.

## 7. Deviations from the package

- **D1 — Unattended drivers.** The executor's per-command timeout is shorter
  than the preflight loop and the matrix, so the package's step-3 and step-4
  command blocks were placed verbatim in two owned-path helper scripts,
  `REQ/preflight/run_preflight_all.sh` and `REQ/matrix_driver.sh`, and started
  with `setsid nohup ... &`. Both are returned and are inside the manifest. The
  commands they run are unchanged.
- **D2 — Partial matrix, C3 and C4 only.** `run_matrix.sh` was invoked with the
  two passing conditions as arguments (a documented feature of the script)
  instead of unqualified. Reason in section 4: an unqualified run would have
  burned the ten C1/C2 run ids on `run_cam_eval.sh` refusals. Ten of the twenty
  authorized runs were used; the C1/C2 half of the budget is untouched and the
  run ids `cam_c1_lite3_rig_v{1..5}` and `cam_c2_height_only_v{1..5}` remain
  fresh.
- **D3 — ffprobe path.** The package's block calls bare `ffprobe`, which is not
  on the remote default PATH. The binary inside the pinned environment
  (`official_r2r/official_env_024/bin/ffprobe`, version 8.0) was used by
  prepending that directory to PATH. No reinstallation; no other change.
- **D4 — C1/C2 measured geometry read from stdout.** Because the render stage
  raised, its `detail` block was not persisted for C1 and C2; the height, pitch,
  and offset in section 3.1 were read from the simulator state printed in
  `preflight/<cond>_stdout.txt`, and the floor numbers from the recorded
  traceback. No preflight was re-run.

No other deviation. The four condition YAMLs, the derived eval config,
`conditions.json`, the launcher, the matrix runner, the preflight, and the
summariser were executed exactly as authored and verified by hash on the remote
before use.

## 8. Remaining issues and what the lead must decide

1. **C1 and C2 are unexecuted and blocked.** Their preflight fails only the
   floor z-depth sub-check, while the objective sensor-state checks (height,
   pitch sign, forward offset) pass. Per the package's own "Open questions" the
   numbers and PNGs are returned rather than acted on. The lead needs to decide
   whether the sub-check's expectation model should account for the agent
   origin-to-floor gap described in section 3.3, and, if so, re-issue the two
   conditions; 10 of the 20 authorized runs remain available for them.
2. **C4's preflight pass carries little margin** (+24.4 % against a 25 %
   tolerance) and, on the section 3.3 reading, passed for the same reason C3
   did rather than because its expectation was right. Its ten episodes are
   nonetheless real runs at a verified 0.65 m / 15 deg / HFOV 54 geometry.
3. **AC2 cannot be ticked as written** — it requires four passing preflight
   reports. AC3 is satisfied for the ten executed runs only. AC4, AC5, and the
   manifest half of AC6 are satisfied for B0, C3, and C4.
4. The executor made no judgement on the mount recommendation; with C1 and C2
   missing, the Lite3-faithful geometry has no data.
5. Commit status: **nothing staged, nothing committed.** The Trellis task
   remains at `review`.

---

# Round 2 (2026-09-10): C1 and C2 after the criterion revision

**Headline.** Under the revised implied-gap criterion **C2 passed preflight and
its five runs completed with exit 0 and no timeouts**. **C1 still does not pass
preflight, but the blocker moved**: it now clears the revised floor check
(implied gap 0.1576 m, inside the new bound) and every direct sensor-state
check, and fails one stage later, at stage 6
`tilt_angle 0 but look_down changed the frame`. Per the package's round-2 step
3 C1 was **not run**; its report, PNGs, and a new read-only diagnostic are
returned instead. **5 of the 10 remaining authorized runs were used; the five
`cam_c1_lite3_rig_v1..v5` run ids remain fresh.**

Nothing was staged or committed. No model, evaluator, condition, protocol,
geometry, sign, or acceptance criterion was changed. No process the executor
did not start was stopped or touched; the resident `isaac-sim` container and an
unrelated user `tar | zstd` job ran throughout. Round-1 evidence was deleted on
neither side.

## R2.1 Sync Gate in (round-2 step 1) — PASSED

```bash
# local, from EXP
rsync -av --exclude '.DS_Store' --exclude '._*' --exclude '__pycache__' \
  public_scenes/requests/2026-09-10_lite3_camera_ablation/ \
  rented4090:/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090/public_scenes/requests/2026-09-10_lite3_camera_ablation/
rsync -av --exclude '._*' \
  public_scenes/configs/vln_cam_c{1,2,3,4}_*.yaml \
  public_scenes/configs/habitat_dual_system_cam_cfg.py \
  rented4090:/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090/public_scenes/configs/

# remote, from the EXP root
sha256sum -c public_scenes/requests/2026-09-10_lite3_camera_ablation/authored_files.sha256
sha256sum work/InternNav/internnav/habitat_extensions/vln/habitat_vln_evaluator.py
```

- `authored_files.sha256`: **15 of 15 lines OK**, exit 0 (also verified locally
  with `shasum -a 256 -c` before the push: 15 of 15 OK).
- Remote worktree evaluator hash still
  `a05268d5e4fac8ab6147d2c828e16ae76d413fe074d2e7f0f99e26ae6fcbf3e7`,
  equal to the pinned baseline.
- The revised `conditions.json`, `preflight_cam.py`, `run_matrix.sh`,
  `OPUS_EXECUTION_PACKAGE.md`, `provenance.json`, and the lead's
  `preflight/round1_failed_ratio_criterion/` archive were transferred. Nothing
  was deleted on either side; the ten round-1 run directories and their
  supervisor records are untouched (verified before the run: the remote held
  exactly `cam_c3_fov_only_v1..v5` and `cam_c4_raised_mount_v1..v5`, and no
  `cam_c1_*` or `cam_c2_*` path existed).
- `__pycache__` was excluded from both directions; it holds no evidence and the
  round-1 manifest contains none.

## R2.2 Resource check (round-2 step 2) — PASSED, no waiting needed

`REQ/preflight/resources_before_round2.txt` (2026-09-10T10:44:13Z).

| Item | Value |
| --- | --- |
| Device | NVIDIA GeForce RTX 4090, 24,564 MiB, driver 575.57.08, CUDA 12.9 |
| Used before the matrix | 2,903 MiB |
| **Free before the matrix** | **21,179 MiB** |
| Resident GPU process | PID 1251 `/isaac-sim/kit/kit`, 2,859 MiB, untouched |
| Other resident load | PID 43996 `tar ... | zstd` under `/home/ubuntu/sun/machine_dog_trials/2026-09-09_tlc_calib_landmark`, CPU and disk only, not started by the executor, untouched |
| Host | 62 GB RAM (57 GB available), 42 GB free on `/` |

Free memory equalled round 1 exactly, so the polling branch was not entered.
Observed peak device memory during the five runs: **22,385 MiB** (130 samples),
i.e. about 19,482 MiB of evaluator on top of the resident Isaac Sim — the same
footprint as round 1. No CUDA out-of-memory occurred.

## R2.3 Preflight (round-2 step 3) — C2 PASSED, C1 FAILED at stage 6

```bash
cd /home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
bash public_scenes/scripts/link_launch_dir.sh
cd work/InternNav
mkdir -p public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight
for c in c1_lite3_rig c2_height_only; do
  CAM_YAML=public_scenes/configs/vln_cam_$c.yaml \
    ../../official_r2r/official_env_024/bin/python \
    public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight_cam.py --cond $c \
    2>&1 | tee public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight/${c}_stdout.txt
done
```

Run unattended through `REQ/preflight/run_preflight_round2.sh` (Deviation R2-D1).
`link_launch_dir.sh` reported `LAUNCH_LINKS_DONE` with all seven paths OK
(`REQ/preflight/link_launch_dir_round2.txt`).

### R2.3.1 Result per condition

| Cond | Verdict | Height (meas./spec) | Pitch down (meas./spec) | Forward offset (meas./spec) | Floor z-depth p90 meas./expected | Ratio | **Implied gap** | Bound |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 `c1_lite3_rig` | **FIRST_BLOCKER: look_down/look_up behave per tilt_angle** | 0.4200 / 0.42 m | 20.000 / 20 deg | 0.2500 / 0.25 m | 0.850 / 0.618 m | 1.3751 | **0.1576 m** | in [-0.05, 0.30] |
| C2 `c2_height_only` | **ALL_STAGES_PASSED** | 0.4200 / 0.42 m | -0.000 / 0 deg | 0.2500 / 0.25 m | 0.996 / 0.723 m | 1.3773 | **0.1584 m** | in [-0.05, 0.30] |

Both conditions therefore **pass the revised stage 5** in full, including the
floor sub-check that blocked them in round 1. The two implied gaps, 0.1576 m
and 0.1584 m, sit inside the round-1 range 0.158-0.163 m measured for all four
conditions, so the lead's navmesh-gap reading is confirmed by an independent
measurement rather than assumed. Stage-5 numbers are now persisted in the
report even on failure, as the lead intended: C1's `stages[5].detail` and
`partial_details` both carry them.

Reference values also recorded: C1 `reference_ground_distance_m_h_over_tan`
0.485 m, vfov 41.828 deg, top-row median depth 7.829 m; C2 0.679 m, vfov
63.453 deg, top-row median depth 8.154 m. Start pose identical for both,
episode 1, agent at `[-1.967646837234497, 0.20027944445610046,
12.827132225036621]`.

C2 also passed stage 6 (`tilt_angle 15`: pitch 0 -> 15.0 -> 0, frame changed as
required) and stage 7 (free 21,163 MiB against a required 19,478 MiB, margin
1,685 MiB). Four PNGs were written for the two conditions
(`REQ/preflight/{c1_lite3_rig,c2_height_only}_start_{rgb,depth_mm}.png`); the
round-1 copies the lead archived are untouched, and the round-2 C1 report,
stdout, and both PNGs are additionally archived under
`REQ/preflight/round2_c1_stage6_blocked/`.

### R2.3.2 C1: exactly what failed, with a read-only diagnostic

```
RuntimeError: tilt_angle 0 but look_down changed the frame   # preflight_cam.py:351
```

Stage 6 requires that with `tilt_angle: 0` a `look_down` step leaves the frame
**bit-identical**. C1's frame changed. C4 has the same `tilt_angle: 0` and
passed this stage in round 1, so the executor characterised the difference
without touching any criterion, using
`REQ/preflight/diag_round2_tilt_noop.py` (new, owned path, read-only: it loads
the same config, renders, steps, and reports differences; it starts no
evaluator and writes only into `REQ/preflight`). Reports:
`diag_round2_tilt_noop_c1_lite3_rig.json` and
`diag_round2_tilt_noop_c4_raised_mount.json`.

| Measurement | C1 (pitch 20 deg) | C4 control (pitch 15 deg) |
| --- | --- | --- |
| Two consecutive renders, no action | identical | identical |
| `before` vs `env.step('look_down')` obs | **939 / 307,200 pixels differ (0.31 %)**, max channel delta 42 | identical |
| Sensor **position** before vs after | unchanged, `[-1.7188284397125244, 0.6202794313430786, 12.802854537963867]` | unchanged |
| Sensor **pitch** before vs after | 20.00000163894477 -> 20.000001093464206 deg, i.e. **-5.5e-7 deg** | 15.000000940225505 deg, unchanged |
| Sensor quaternion w | 0.7293933629989624 -> 0.7293934226036072 (about 6e-8, 1-2 ULP) | unchanged |
| Quaternion norm | 0.999999945608767 -> 1.0000000302622762 | 1.0000000029311282 -> unchanged |
| A **second** `look_down` | frame identical to the first, pitch unchanged | identical |
| `look_up` afterwards | frame identical to the first look_down result, pitch unchanged | identical |
| Rendering itself | deterministic (0 differing pixels with no action) | deterministic |

Reading of these numbers, offered to the lead and **not acted on**: the
zero-degree `look_down` does not move the camera. It re-normalises the sensor
quaternion by one to two ULPs, which rotates the view by 5.5e-7 degrees —
roughly 10^6 times below the preflight's own 0.5-degree pitch tolerance — and
that sub-microdegree rotation flips 0.31 percent of pixels where a geometric
edge falls on a sample boundary, with the rest of the frame bit-identical. The
transform is idempotent: a second `look_down` and the following `look_up`
change nothing further. C4 escapes only because its start quaternion is already
exactly normalised at this pose, so nothing shifts; this is a property of the
particular float values, not of the condition's geometry. On this reading the
stage-6 exact-pixel-equality test, not C1's configuration, is what fails — but
confirming that would require changing the stage-6 acceptance criterion, which
is outside the executor's scope, so **nothing was altered and C1 was not run**.
This is an interpretation of returned numbers, not a verified root cause in
habitat-sim's source.

Note also that C4 ran ten episodes in round 1 with the same `tilt_angle: 0`, so
whatever the evaluator does with its look-down steps under a zero tilt has
already been exercised at 0.65 m; C1 differs from it only in height, pitch, and
the quaternion happening to need re-normalisation.

## R2.4 Matrix (round-2 step 4) — 5 runs, all exit 0; C1 skipped by the gate

```bash
cd /home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
bash public_scenes/requests/2026-09-10_lite3_camera_ablation/run_matrix.sh \
  c1_lite3_rig c2_height_only
```

Run unattended through `REQ/matrix_driver_round2.sh` (Deviation R2-D1), which
appends to the round-1 `matrix_stdout.txt`. The package's command was issued
**with both conditions named**, exactly as the round-2 step writes it: the
lead's revised `run_matrix.sh` now gates on the preflight verdict, so C1 was
refused by the matrix itself before any run id was consumed —

```
SKIP condition c1_lite3_rig: preflight report did not pass all stages
```

That gate was verified against both reports before launching. `run_cam_eval.sh`
was never reached for C1, so **no C1 run id was burned** and no refusal
directory exists.

`REQ/matrix_log.jsonl`, the five new lines (round-1 lines 1-10 unchanged):

| Run id | Condition | exit_code | timed_out | wall s | deadline s |
| --- | --- | --- | --- | --- | --- |
| cam_c2_height_only_v1 | c2_height_only | 0 | false | 118.0 | 1800 |
| cam_c2_height_only_v2 | c2_height_only | 0 | false | 146.6 | 1800 |
| cam_c2_height_only_v3 | c2_height_only | 0 | false | 132.7 | 1800 |
| cam_c2_height_only_v4 | c2_height_only | 0 | false | 136.3 | 1800 |
| cam_c2_height_only_v5 | c2_height_only | 0 | false | 127.3 | 1800 |

- Matrix wall time 2026-09-10T10:50:14Z to 11:01:15Z, about **11 minutes**;
  slowest run 146.6 s, 8 percent of its 1,800 s deadline.
- **Authorized-run budget: 20 authorized, 10 used in round 1, 5 used in round 2,
  5 unused (`cam_c1_lite3_rig_v1..v5`).**
- Five directories `public_scenes/runs/cam_c2_height_only_v{1..5}`, each with
  `progress.json` carrying **two** episode records (verified 5 of 5), plus
  `inputs.json`, `result.json`, `exit.json` (all `exit_code: 0`),
  `environment.json`, `gpu_samples_every_5s.csv`, `trace_0/`, `vis_0/`,
  `vis_debug/`, `check_sim_0/`.
- Five supervisor records `runs/cam_c2_height_only_v{1..5}` with `meta.json`,
  `stdout.log`, `stderr.log`, `process.json`.
- No run was deleted or rerun under an existing id; no OOM; the two-consecutive-
  OOM stop rule was never triggered.
- Input identity: all five runs record SHA-256 **identical to
  `public_eval_v5`** for `scripts/eval/eval.py`, the evaluator,
  `internnav/model/utils/vln_utils.py`, the scene `.glb`, the `.navmesh`, and
  the frozen `val_unseen.json.gz` — **0 mismatches**.

## R2.5 Summary and media checks (round-2 step 5) — PASSED

```bash
official_r2r/official_env_024/bin/python \
  public_scenes/requests/2026-09-10_lite3_camera_ablation/summarise_conditions.py
PATH=.../official_r2r/official_env_024/bin:$PATH python3 <the package's ffprobe block>
```

- **B0 gate holds: the summariser again reproduced the recorded baseline
  exactly — episode 1 3/5, episode 2 2/5.**
- **60 MP4s probed over all 15 `cam_*` runs, 0 decode errors** (round 1's 40
  plus 20 new).
- **30 of 30 `vis_debug` videos have a frame count equal to the `steps` value
  recorded in `progress.json`** for the matching episode.

### `condition_summary.md` (all conditions, regenerated over 30 runs)

| Condition | Height | Pitch | HFOV | Tilt | Ep1 success | Ep1 NE m (min/med/max) | Ep2 success | Ep2 NE m (min/med/max) | Ep2 collisions (min/med/max) | Learned STOP | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 baseline (recorded) | 1.25 m | 0 deg | 79 | 15 | 3/5 | 1.05/1.252/4.057 | 2/5 | 2.154/4.892/5.911 | 8/10/10 | 10/10 | 5/10 |
| c1_lite3_rig (Lite3 rig faithful) | 0.42 m | 20 deg | 54 | 0 | 0/0 | - | 0/0 | - | - | 0/0 | 0/0 |
| c2_height_only (Height only) | 0.42 m | 0 deg | 79 | 15 | 3/5 | 1.26/1.415/4.677 | 2/5 | 2.88/3.059/8.467 | 7/13/19 | 10/10 | 5/10 |
| c3_fov_only (FOV only) | 1.25 m | 0 deg | 54 | 15 | 2/5 | 1.208/13.877/16.3 | 1/5 | 2.488/5.424/9.045 | 2/4/4 | 10/10 | 3/10 |
| c4_raised_mount (Raised mount candidate) | 0.65 m | 15 deg | 54 | 0 | 2/5 | 0.785/14.45/16.901 | 0/5 | 4.505/8.931/10.202 | 17/40/58 | 10/10 | 2/10 |

The `0/0` row for C1 means "no runs recorded", not a zero score. C3 and C4 rows
are unchanged from round 1.

Supporting detail for the new condition (executor transcription from
`condition_summary.json`; the lead recomputes from `progress.json` and the
traces per AC4):

| Condition / episode | Success | Oracle success | Entered radius | Learned STOP | Steps min/med/max | Collisions min/med/max | S2 level_view / look_down_followup | Pixel goals min/med/max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 ep1 | 3/5 | 3 | 3 | 5/5 | 63/80/81 | 0/0/0 | 53 / 37 | 6/8/8 |
| B0 ep2 | 2/5 | 5 | 5 | 5/5 | 86/107/116 | 8/10/10 | 66 / 55 | 9/12/12 |
| **C2 ep1** | **3/5** | 3 | 3 | 5/5 | 53/76/92 | 0/0/0 | 57 / 39 | 5/8/10 |
| **C2 ep2** | **2/5** | 4 | 4 | 5/5 | 91/98/128 | 7/13/19 | 71 / 60 | 10/11/14 |

Per-run outcome for C2 (episode_id, success, steps): v1 (1, 0.0, 53) (2, 1.0,
98); v2 (1, 1.0, 76) (2, 0.0, 125); v3 (1, 0.0, 59) (2, 0.0, 128); v4 (1, 1.0,
92) (2, 1.0, 94); v5 (1, 1.0, 91) (2, 0.0, 91).

All ten new episodes ended on a learned System-2 STOP; none hit the 500-step
cap or the deadline. Stated descriptively, with attribution to System 1 or
System 2 outside this test's claim boundary: C2 matches the baseline's success
counts on both episodes (3/5 and 2/5) at a third of the camera height, with a
tighter episode-2 navigation-error spread (2.88-8.467 m against B0's
2.154-5.911 m, median 3.059 against 4.892), more episode-2 collisions
(7-19 against 8-10), and a markedly higher `s1_stop_mid_segment` count on
episode 1 (14 against B0's 2) with correspondingly fewer
`forward_budget_exhausted` events (25 against 35). One episode-2 run did not
enter the goal radius (4 of 5 against B0's 5 of 5).

Observation on the recorded baseline, unrelated to round 2 and not acted on:
`public_eval_v1` records evaluator hash
`0fd895d1caae31e254d06a8a45ed34c1799a2a33e1c561696fe9fafa765a2b37` while
`public_eval_v2..v5` and all fifteen `cam_*` runs record the pinned
`a05268d5...`. `condition_summary.json` therefore reports two hashes in B0's
`evaluator_sha256_set`. This predates both rounds and is inside frozen baseline
evidence, so it was left alone.

## R2.6 Manifest and Sync Gate out (round-2 step 6) — PASSED

```bash
# remote, from the EXP root, after the last evidence edit
find public_scenes/runs/cam_* runs/cam_* public_scenes/requests/2026-09-10_lite3_camera_ablation -type f \
  ! -name manifest.sha256 ! -name OPUS_RETURN.md -print0 | sort -z | xargs -0 sha256sum \
  > public_scenes/requests/2026-09-10_lite3_camera_ablation/manifest.sha256

# local, from the EXP root
rsync -a "rented4090:.../public_scenes/runs/cam_c2_height_only_v*" public_scenes/runs/
rsync -a "rented4090:.../runs/cam_c2_height_only_v*" runs/
rsync -a rented4090:.../public_scenes/requests/2026-09-10_lite3_camera_ablation/ \
         public_scenes/requests/2026-09-10_lite3_camera_ablation/
shasum -a 256 -c public_scenes/requests/2026-09-10_lite3_camera_ablation/manifest.sha256
```

- Manifest: **1,091 files** (round 1: 787), covering all fifteen `cam_*` run
  directories, all fifteen supervisor records, and the whole request directory.
  Remote self-verification: 0 non-OK lines.
- **Local verification: 1,091 of 1,091 lines OK, exit 0.**
- Transferred back: 263 files / 207,605,413 bytes of run evidence, 20 files /
  739,171 bytes of supervisor records, 27 files / 1,568,101 bytes of request
  files.

Returned local paths (all under `EXP`), new in round 2:

- `public_scenes/runs/cam_c2_height_only_v{1..5}/`
- `runs/cam_c2_height_only_v{1..5}/`
- `public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight/`:
  `c1_lite3_rig.json`, `c2_height_only.json`, four PNGs, two `_stdout.txt`,
  `resources_before_round2.txt`, `link_launch_dir_round2.txt`,
  `preflight_round2_stdout.txt`, `run_preflight_round2.sh`,
  `diag_round2_tilt_noop.py`, `diag_round2_tilt_noop_c1_lite3_rig.json`,
  `diag_round2_tilt_noop_c4_raised_mount.json`, both diagnostic stdout files,
  and `round2_c1_stage6_blocked/` (C1's round-2 report, stdout, and both PNGs)
- `public_scenes/requests/2026-09-10_lite3_camera_ablation/`:
  `matrix_driver_round2.sh`, `matrix_driver_round2_stdout.txt`, updated
  `matrix_log.jsonl`, `matrix_log.jsonl.txt`, `matrix_stdout.txt`,
  `condition_summary.json`, `condition_summary.md`, `ffprobe_frame_counts.json`,
  `manifest.sha256`, and this `OPUS_RETURN.md`

`OPUS_RETURN.md` was written after the manifest, is deliberately excluded from
it, and was copied to the remote afterwards. Round-1 files were preserved on
both sides, including `preflight/round1_failed_ratio_criterion/`.

## R2.7 Deviations from the round-2 package steps

- **R2-D1 — Unattended drivers.** As in round 1, the executor's per-command
  timeout is shorter than the preflight loop and the matrix, so the package's
  commands were placed verbatim in two owned-path helper scripts,
  `REQ/preflight/run_preflight_round2.sh` and `REQ/matrix_driver_round2.sh`,
  and started with `setsid nohup ... &`. New files rather than edits to the
  round-1 helpers, so round-1 evidence stays byte-identical. The commands they
  run are unchanged; the matrix driver passes the package's own condition
  arguments and appends to `matrix_stdout.txt`.
- **R2-D2 — C1 not run (5 of 10 remaining runs used).** Directed by the
  package's round-2 step 3 ("If either still fails, return the report and PNGs
  and do not run it"). C1's five run ids are untouched.
- **R2-D3 — Added read-only diagnostic.** `REQ/preflight/diag_round2_tilt_noop.py`
  was written to quantify C1's stage-6 failure (section R2.3.2). It is new, in
  an owned path, starts no evaluator, consumes no authorized run, changes no
  criterion or geometry, and writes only into `REQ/preflight`. It was run once
  for C1 and once for C4 as a control. Not covered by
  `authored_files.sha256`, like the round-1 helper scripts; it is inside
  `manifest.sha256`.
- **R2-D4 — ffprobe path.** Unchanged from round-1 D3: bare `ffprobe` is not on
  the remote default PATH, so `official_r2r/official_env_024/bin` was
  prepended. No reinstallation.
- **R2-D5 — `__pycache__` excluded from rsync.** A local
  `REQ/__pycache__/preflight_cam.cpython-312.pyc` exists from the lead's local
  work; it is not evidence, was excluded in both directions, and the remote
  request directory contains no `.pyc` (verified before the manifest).
- **R2-D6 — Round-2 C1 artefacts additionally archived.** Before the diagnostic
  ran, C1's round-2 report, stdout, and both PNGs were copied to
  `REQ/preflight/round2_c1_stage6_blocked/`, mirroring the lead's round-1
  archive so a third round cannot silently overwrite them.

No other deviation. `conditions.json`, the four condition YAMLs, the eval
config, the preflight, the launcher, the matrix runner, and the summariser were
executed exactly as authored and hash-verified on the remote before use.

## R2.8 Remaining issues and what the lead must decide

1. **C1 remains unexecuted, now for a different reason.** The revised
   implied-gap criterion did what it was meant to do: C1's stage 5 passes with a
   0.1576 m gap. The new blocker is stage 6's requirement that a zero-degree
   `look_down` leave the frame bit-identical, which the diagnostic attributes to
   a 1-2 ULP quaternion re-normalisation worth 5.5e-7 degrees. Deciding whether
   that test should admit a tolerance is a criterion change and belongs to the
   lead. Five authorized runs remain for C1 if it is re-issued.
2. **AC2 still cannot be ticked as written** (four passing preflight reports);
   three of four conditions now pass. AC3 is satisfied for the fifteen executed
   runs. AC4, AC5, and the manifest half of AC6 are satisfied for B0, C2, C3,
   and C4.
3. **The Lite3-faithful geometry still has no data.** C2 isolates the height
   change alone (0.42 m under the unchanged protocol) and matches the baseline
   at 3/5 and 2/5; the combined 0.42 m + 20 deg + HFOV 54 rig is the one
   configuration still unmeasured, so no mount recommendation is offered.
4. Commit status: **nothing staged, nothing committed.** The Trellis task
   remains at `review`.

---

# Round 3 (2026-09-10): C1 executed under the revised tilt no-op criterion

**Headline.** C1 `c1_lite3_rig` **passed all eight preflight stages**, including
the revised stage 6, and the **five remaining authorized runs
`cam_c1_lite3_rig_v1..v5` all completed with exit 0 and no timeout**. The
20-run matrix is now complete: 20 of 20 authorized runs used, all exit 0.
All evidence is back at the local paths and the local manifest verifies
**1,571 / 1,571**.

Nothing was staged or committed. No model, evaluator, condition, protocol,
geometry, sign, or acceptance criterion was changed. No process the executor
did not start was stopped or touched; the resident `isaac-sim` container ran
throughout. Round-1 and round-2 evidence was deleted on neither side.

## R3.1 Sync Gate in (round-3 step 1) — PASSED

```bash
# local, from EXP
rsync -av --exclude '.DS_Store' --exclude '._*' --exclude '__pycache__' \
  public_scenes/requests/2026-09-10_lite3_camera_ablation/ \
  rented4090:/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090/public_scenes/requests/2026-09-10_lite3_camera_ablation/
rsync -av --exclude '._*' \
  public_scenes/configs/vln_cam_c1_lite3_rig.yaml \
  public_scenes/configs/vln_cam_c2_height_only.yaml \
  public_scenes/configs/vln_cam_c3_fov_only.yaml \
  public_scenes/configs/vln_cam_c4_raised_mount.yaml \
  public_scenes/configs/habitat_dual_system_cam_cfg.py \
  rented4090:/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090/public_scenes/configs/

# remote, from the EXP root
sha256sum -c public_scenes/requests/2026-09-10_lite3_camera_ablation/authored_files.sha256
sha256sum work/InternNav/internnav/habitat_extensions/vln/habitat_vln_evaluator.py
```

- `authored_files.sha256`: **15 of 15 lines OK**, exit 0 (also verified locally
  with `shasum -a 256 -c` before the push: 15 of 15 OK).
- Remote worktree evaluator hash still
  `a05268d5e4fac8ab6147d2c828e16ae76d413fe074d2e7f0f99e26ae6fcbf3e7`,
  equal to the pinned baseline.
- Five files changed on the push — the lead's round-3 revisions to
  `conditions.json`, `preflight_cam.py`, `OPUS_EXECUTION_PACKAGE.md`,
  `authored_files.sha256`, and `provenance.json`. The four condition YAMLs and
  the eval config were already byte-identical.
- Nothing was deleted on either side. Before the run the remote held exactly
  the fifteen round-1/2 directories (`cam_c2_height_only_v1..v5`,
  `cam_c3_fov_only_v1..v5`, `cam_c4_raised_mount_v1..v5`) and **no
  `cam_c1_*` path**, so no run id was reused.
- Both earlier C1 archives were confirmed present on the remote before the
  preflight overwrote the live report:
  `preflight/round1_failed_ratio_criterion/` and
  `preflight/round2_c1_stage6_blocked/`.
- `__pycache__` was excluded in both directions; the remote request directory
  contains no `.pyc` (verified).

## R3.2 Resource check (round-3 step 2) — PASSED, no waiting needed

`REQ/preflight/resources_before_round3.txt` (2026-09-10T11:13:53Z).

| Item | Value |
| --- | --- |
| Device | NVIDIA GeForce RTX 4090, 24,564 MiB, driver 575.57.08, CUDA 12.9 |
| Used before the matrix | 2,903 MiB |
| **Free before the matrix** | **21,179 MiB** |
| GPU utilisation at the snapshot | 9 % |
| Resident GPU process | PID 1251 `/isaac-sim/kit/kit`, 2,859 MiB, untouched |
| Host | 62 GB RAM (57 GB available), 42 GB free on `/` |

Free memory equalled rounds 1 and 2 exactly, so the polling branch was not
entered. The round-2 `tar | zstd` job had finished and no longer appears. Peak
device memory during the five runs: **22,385 MiB** over 482 samples, i.e. about
19,482 MiB of evaluator on top of the resident Isaac Sim — the same footprint as
rounds 1 and 2. No CUDA out-of-memory occurred; the two-consecutive-OOM stop
rule was never approached. The five run directories consumed about 298 MB.

## R3.3 Preflight (round-3 step 3) — C1 **ALL_STAGES_PASSED**

```bash
cd /home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
bash public_scenes/scripts/link_launch_dir.sh
cd work/InternNav
mkdir -p public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight
CAM_YAML=public_scenes/configs/vln_cam_c1_lite3_rig.yaml \
  ../../official_r2r/official_env_024/bin/python \
  public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight_cam.py --cond c1_lite3_rig \
  2>&1 | tee public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight/c1_lite3_rig_stdout.txt
```

Run unattended through `REQ/preflight/run_preflight_round3.sh` (Deviation
R3-D1) at 2026-09-10T11:14:40Z; python exit 0. `link_launch_dir.sh` reported
`LAUNCH_LINKS_DONE` with all seven paths OK
(`REQ/preflight/link_launch_dir_round3.txt`).

All eight stages PASS, `all_stages_passed: true`, `first_blocker: null`:

| # | Stage | Verdict |
| --- | --- | --- |
| 0 | official env versions | PASS (habitat-lab 0.2.4, habitat-sim 0.3.3, torch 2.6.0+cu124, python 3.9.23) |
| 1 | all paths resolve from the launch directory | PASS |
| 2 | pinned inputs match baseline `public_eval_v5` | PASS |
| 3 | condition eval config loads with `CAM_YAML` | PASS |
| 4 | condition habitat config composes to the specified geometry | PASS |
| 5 | start frame renders with the specified height, pitch, and floor distance | **PASS** |
| 6 | `look_down`/`look_up` behave per `tilt_angle` | **PASS** |
| 7 | GPU budget against the baseline footprint | PASS |

### R3.3.1 Stage 5 — measured sensor state and floor geometry

Episode 1, scene `skokloster-castle.glb`, start position
`[-1.967646837234497, 0.20027944445610046, 12.827132225036621]`, 640x480,
vfov 41.828 deg from hfov 54.

| Quantity | Measured | Specified | Verdict |
| --- | --- | --- | --- |
| Sensor height above agent | **0.4200 m** | 0.42 m | exact |
| Sensor pitch down | **20.000 deg** | 20 deg | exact, sign included |
| Sensor forward offset | **0.2500 m** | 0.25 m | exact |
| Floor z-depth p90, bottom 16 rows | **0.850 m** | flat-floor expectation **0.618 m** | ratio **1.3751** |
| **Implied agent-origin-to-floor gap** | **0.1576 m** | bounds [-0.05, 0.30] m | **inside** |

Reference values also recorded: `reference_ground_distance_m_h_over_tan`
0.485 m, top-row median depth 7.829 m. The implied gap is bit-identical to the
round-2 measurement (0.1576 m), so the revised criterion changed the verdict
without changing the measurement.

### R3.3.2 Stage 6 — the revised tilt no-op check

| Quantity | Measured | Limit (`conditions.json`) | Verdict |
| --- | --- | --- | --- |
| `changed_pixel_fraction_after_look_down` | **0.003057** (0.31 %) | `tilt_noop_max_changed_pixel_fraction` 0.01 (1 %) | **inside** |
| `pitch_delta_deg_after_look_down` | **-1e-06 deg** | `tilt_noop_max_pitch_delta_deg` 0.01 | **inside** |
| `frame_identical_after_look_down` | false | not a criterion any more | recorded only |
| `mean_abs_channel_delta_after_look_down` | 0.001381 | — | recorded only |
| pitch before / after look_down / after look_up | 20.0 / 20.0 / 20.0 deg | — | restored |

Both numbers match the lead's round-3 expectation ("about 0.003" and "about 0")
and reproduce the round-2 diagnostic: the changed fraction 0.31 percent and the
sub-microdegree pitch delta are the same phenomenon, now inside an explicit
bound instead of failing an exact-equality test.

Stage 7: free 21,163 MiB against a required 19,478 MiB, margin 1,685 MiB,
resident compute app recorded and untouched.

Two PNGs were rewritten for lead inspection
(`REQ/preflight/c1_lite3_rig_start_rgb.png`,
`c1_lite3_rig_start_depth_mm.png`); the round-1 and round-2 archived copies are
untouched.

## R3.4 Matrix (round-3 step 4) — 5 runs, all exit 0, no timeouts

```bash
cd /home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
bash public_scenes/requests/2026-09-10_lite3_camera_ablation/run_matrix.sh c1_lite3_rig
```

Run unattended through `REQ/matrix_driver_round3.sh` (Deviation R3-D1), which
appends to `matrix_stdout.txt`. The preflight gate in `run_matrix.sh` was
verified to pass against the new report before launching, and no `cam_c1_*`
run id existed.

`REQ/matrix_log.jsonl`, the five new lines (rounds 1-2 lines 1-15 unchanged):

| Run id | Condition | exit_code | timed_out | wall s | deadline s |
| --- | --- | --- | --- | --- | --- |
| cam_c1_lite3_rig_v1 | c1_lite3_rig | 0 | false | 416.9 | 1800 |
| cam_c1_lite3_rig_v2 | c1_lite3_rig | 0 | false | 277.7 | 1800 |
| cam_c1_lite3_rig_v3 | c1_lite3_rig | 0 | false | 181.5 | 1800 |
| cam_c1_lite3_rig_v4 | c1_lite3_rig | 0 | false | 148.3 | 1800 |
| cam_c1_lite3_rig_v5 | c1_lite3_rig | 0 | false | 189.2 | 1800 |

- Matrix wall time 2026-09-10T11:16:04Z to 11:36:18Z, about **20 minutes**;
  slowest run 416.9 s, 23 percent of its 1,800 s deadline. C1 runs are about
  three times longer than C2's (118-147 s) because its episodes take more steps.
- **Authorized-run budget: 20 authorized, 10 used in round 1, 5 in round 2,
  5 in round 3 — 20 of 20 used, 0 remaining.**
- Five directories `public_scenes/runs/cam_c1_lite3_rig_v{1..5}`, each with
  `progress.json` carrying **two** episode records (verified 5 of 5), plus
  `inputs.json`, `result.json`, `exit.json` (all `exit_code: 0`),
  `environment.json`, `gpu_samples_every_5s.csv`, `trace_0/`, `vis_0/`,
  `vis_debug/`, `check_sim_0/`.
- Five supervisor records `runs/cam_c1_lite3_rig_v{1..5}` with `meta.json`,
  `stdout.log`, `stderr.log`, `process.json`.
- No run was deleted or rerun under an existing id; no OOM (0 of 5 stderr logs
  contain "CUDA out of memory").
- Input identity: all five runs record SHA-256 **identical to
  `public_eval_v5`** for the six shared inputs — `scripts/eval/eval.py`, the
  evaluator, `internnav/model/utils/vln_utils.py`, the scene `.glb`, the
  `.navmesh`, and the frozen `val_unseen.json.gz` — **0 mismatches**. The only
  differing input keys are the condition's own config files
  (`habitat_dual_system_cam_cfg.py`, `vln_cam_c1_lite3_rig.yaml`,
  `conditions.json`), which differ by design.
- `evaluator_sha256_set` for C1 is the single pinned `a05268d5...`.

## R3.5 Summary and media checks (round-3 step 5) — PASSED, one recorded anomaly

```bash
official_r2r/official_env_024/bin/python \
  public_scenes/requests/2026-09-10_lite3_camera_ablation/summarise_conditions.py
PATH=.../official_r2r/official_env_024/bin:$PATH python3 <the package's ffprobe block>
```

- **B0 gate holds: the summariser again reproduced the recorded baseline
  exactly — episode 1 3/5, episode 2 2/5.**
- **80 MP4s probed over all 20 `cam_*` runs, 0 decode errors** (rounds 1-2's 60
  plus 20 new).
- **39 of 40 `vis_debug` videos have a frame count equal to the `steps` value
  in `progress.json`.** The single exception is recorded in R3.8 item 1.

### `condition_summary.md` (all conditions, regenerated over 40 runs)

| Condition | Height | Pitch | HFOV | Tilt | Ep1 success | Ep1 NE m (min/med/max) | Ep2 success | Ep2 NE m (min/med/max) | Ep2 collisions (min/med/max) | Learned STOP | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 baseline (recorded) | 1.25 m | 0 deg | 79 | 15 | 3/5 | 1.05/1.252/4.057 | 2/5 | 2.154/4.892/5.911 | 8/10/10 | 10/10 | 5/10 |
| c1_lite3_rig (Lite3 rig faithful) | 0.42 m | 20 deg | 54 | 0 | 1/5 | 1.063/12.184/16.941 | 0/5 | 4.267/11.996/14.788 | 9/15/83 | 9/10 | 1/10 |
| c2_height_only (Height only) | 0.42 m | 0 deg | 79 | 15 | 3/5 | 1.26/1.415/4.677 | 2/5 | 2.88/3.059/8.467 | 7/13/19 | 10/10 | 5/10 |
| c3_fov_only (FOV only) | 1.25 m | 0 deg | 54 | 15 | 2/5 | 1.208/13.877/16.3 | 1/5 | 2.488/5.424/9.045 | 2/4/4 | 10/10 | 3/10 |
| c4_raised_mount (Raised mount candidate) | 0.65 m | 15 deg | 54 | 0 | 2/5 | 0.785/14.45/16.901 | 0/5 | 4.505/8.931/10.202 | 17/40/58 | 10/10 | 2/10 |

Every condition now carries data; the round-2 `0/0` placeholder row for C1 is
gone. C2, C3, and C4 rows are unchanged from the earlier rounds.

Supporting detail for the new condition (executor transcription from
`condition_summary.json`; the lead recomputes from `progress.json` and the
traces per AC4):

| Condition / episode | Success | Oracle success | Entered radius | Learned STOP | Steps min/med/max | Collisions min/med/max | S2 level_view / look_down_followup | Pixel goals min/med/max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 ep1 | 3/5 | 3 | 3 | 5/5 | 63/80/81 | 0/0/0 | 53 / 37 | 6/8/8 |
| B0 ep2 | 2/5 | 5 | 5 | 5/5 | 86/107/116 | 8/10/10 | 66 / 55 | 9/12/12 |
| **C1 ep1** | **1/5** | 2 | 2 | 5/5 | 89/106/125 | 8/10/21 | 79 / 56 | 9/11/13 |
| **C1 ep2** | **0/5** | 0 | 0 | **4/5** | 111/155/501 | 9/15/83 | 178 / 137 | 13/18/53 |

Per-run outcome for C1 (episode_id, success, steps, navigation error m):
v1 (1, 0.0, 117, 16.941) (2, 0.0, 501, 6.945); v2 (1, 0.0, 89, 12.184)
(2, 0.0, 345, 13.808); v3 (1, 0.0, 106, 3.081) (2, 0.0, 155, 11.996);
v4 (1, 0.0, 98, 12.652) (2, 0.0, 111, 4.267); v5 (1, 1.0, 125, 1.063)
(2, 0.0, 154, 14.788).

Termination reasons: C1 episode 1 `habitat_episode_over` 5/5; C1 episode 2
`habitat_episode_over` 4/5 and `evaluator_step_cap` 1/5. This is the **only
step-cap termination in all 20 `cam_*` runs**; every other episode in the whole
matrix, and every baseline episode, ended on a learned System-2 STOP.

Stated descriptively, with attribution to System 1 or System 2 outside this
test's claim boundary: the faithful Lite3 rig is the weakest of the five
configurations, 1 of 10 episodes successful against B0's 5 of 10, and it is the
only condition where episode 2 never entered the goal radius and never achieved
oracle success. Its episode-2 non-terminal stop events are far more numerous
than the baseline's (`forward_budget_exhausted` 100, `s1_stop_mid_segment` 36)
and its S2 call load is roughly triple (level_view 178, look_down_followup 137).
C2, which changes only the height, matches the baseline exactly at 3/5 and 2/5,
so on this two-episode functional test the degradation is associated with the
combination that C1 adds on top of the height — the 54-degree HFOV and the
fixed 20-degree downward pitch with no look-down tilt — and not with the
0.42 m height by itself. Two frozen episodes and five unseeded runs are not
enough to rank the conditions statistically; this is a functional signal, not a
benchmark result.

## R3.6 Manifest and Sync Gate out (round-3 step 6) — PASSED

```bash
# remote, from the EXP root, after the last evidence edit
find public_scenes/runs/cam_* runs/cam_* public_scenes/requests/2026-09-10_lite3_camera_ablation -type f \
  ! -name manifest.sha256 ! -name OPUS_RETURN.md -print0 | sort -z | xargs -0 sha256sum \
  > public_scenes/requests/2026-09-10_lite3_camera_ablation/manifest.sha256

# local, from the EXP root
rsync -a "rented4090:.../public_scenes/runs/cam_c1_lite3_rig_v*" public_scenes/runs/
rsync -a "rented4090:.../runs/cam_c1_lite3_rig_v*" runs/
rsync -a --exclude '__pycache__' rented4090:.../public_scenes/requests/2026-09-10_lite3_camera_ablation/ \
         public_scenes/requests/2026-09-10_lite3_camera_ablation/
shasum -a 256 -c public_scenes/requests/2026-09-10_lite3_camera_ablation/manifest.sha256
```

- Manifest: **1,571 files** (round 1: 787; round 2: 1,091), covering all twenty
  `cam_*` run directories, all twenty supervisor records, and the whole request
  directory. Remote self-verification: 0 non-OK lines.
- **Local verification: 1,571 of 1,571 lines OK, exit 0.**
- Transferred back: 451 files / 303,129,492 bytes of run evidence, 20 files /
  802,755 bytes of supervisor records, 18 files / 762,157 bytes of request
  files.

Returned local paths (all under `EXP`), new in round 3:

- `public_scenes/runs/cam_c1_lite3_rig_v{1..5}/`
- `runs/cam_c1_lite3_rig_v{1..5}/`
- `public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight/`:
  `c1_lite3_rig.json` (now passing), `c1_lite3_rig_start_rgb.png`,
  `c1_lite3_rig_start_depth_mm.png`, `c1_lite3_rig_stdout.txt`,
  `resources_before_round3.txt`, `link_launch_dir_round3.txt`,
  `preflight_round3_stdout.txt`, `run_preflight_round3.sh`
- `public_scenes/requests/2026-09-10_lite3_camera_ablation/`:
  `matrix_driver_round3.sh`, `matrix_driver_round3_stdout.txt`,
  `summarise_round3_stdout.txt`, `ffprobe_round3.py`,
  `ffprobe_round3_stdout.txt`, updated `matrix_log.jsonl` (20 lines),
  `matrix_log.jsonl.txt`, `matrix_stdout.txt`, `condition_summary.json`,
  `condition_summary.md`, `ffprobe_frame_counts.json`, `manifest.sha256`, and
  this `OPUS_RETURN.md`

`OPUS_RETURN.md` was written after the manifest, is deliberately excluded from
it, and was copied to the remote afterwards. Round-1 and round-2 files were
preserved on both sides, including `preflight/round1_failed_ratio_criterion/`
and `preflight/round2_c1_stage6_blocked/`.

## R3.7 Deviations from the round-3 package steps

- **R3-D1 — Unattended drivers.** As in rounds 1 and 2, the executor's
  per-command timeout is shorter than the preflight and the matrix, so the
  package's commands were placed verbatim in two new owned-path helper scripts,
  `REQ/preflight/run_preflight_round3.sh` and `REQ/matrix_driver_round3.sh`,
  and started with `setsid nohup ... &`. New files rather than edits to the
  round-1/2 helpers, so earlier evidence stays byte-identical. The commands they
  run are unchanged; the matrix driver passes the package's own condition
  argument and appends to `matrix_stdout.txt`.
- **R3-D2 — ffprobe path.** Unchanged from round-1 D3 / round-2 R2-D4: bare
  `ffprobe` is not on the remote default PATH, so
  `official_r2r/official_env_024/bin` was prepended. No reinstallation.
- **R3-D3 — ffprobe block run from a file.** The package's step-5 ffprobe
  heredoc was written to a file so it could run detached under `setsid nohup`
  past the executor's command timeout. The Python is the package's, byte for
  byte; a copy is preserved at `REQ/ffprobe_round3.py` and is inside
  `manifest.sha256`, and its stdout at `REQ/ffprobe_round3_stdout.txt`.
- **R3-D4 — Summariser run detached.** For the same timeout reason the
  summariser was started with `setsid nohup` and its output captured to
  `REQ/summarise_round3_stdout.txt` instead of the terminal. The command is the
  package's, unchanged.
- **R3-D5 — `__pycache__` excluded from rsync.** Unchanged from R2-D5. The
  remote request directory contains no `.pyc` (verified before the manifest).

No other deviation. `conditions.json`, the four condition YAMLs, the eval
config, the preflight, the launcher, the matrix runner, and the summariser were
executed exactly as authored and hash-verified on the remote before use. No
geometry, sign, criterion, or evaluator logic was touched in this round.

## R3.8 Remaining issues and what the lead must decide

1. **One frame-count mismatch, on the only step-capped episode.**
   `cam_c1_lite3_rig_v1` episode 2 has **502** `vis_debug` frames against
   **501** `steps`, the single exception among 40 videos. Its trace footer reads
   `"termination_reason": "evaluator_step_cap", "final_step_id": 501,
   "evaluator_step_cap": 500`, so the episode was cut by the cap rather than by
   a learned STOP, and the video holds one frame more than the recorded final
   step id. The video decodes cleanly; no other run in any round hit the cap, so
   the package's `frames == steps` expectation had never been exercised on this
   path. Reading offered to the lead and **not acted on**: the cap path appears
   to render one frame after recording its final step. Whether the media check
   should read `final_step_id + 1` for cap terminations is a criterion question
   and belongs to the lead. Evidence:
   `public_scenes/runs/cam_c1_lite3_rig_v1/trace_0/skokloster-castle_0002.jsonl`
   (footer), `REQ/ffprobe_frame_counts.json`.
2. **AC2 can now be ticked**: all four conditions have a preflight report with
   `all_stages_passed: true`, C1's obtained under the revised stage-5 and
   stage-6 criteria. AC3 is satisfied for all twenty executed runs (exit 0, no
   timeout). AC4, AC5, and the manifest half of AC6 are satisfied for B0 and
   all four conditions.
3. **The authorized run budget is now fully consumed**: 20 of 20. Any further
   run needs new authorization from Dr Sun.
4. **A mount recommendation is still the lead's call, not the executor's.** The
   data now covers all four conditions, but on two frozen episodes with five
   unseeded runs each; the executor states the numbers and the C1-versus-C2
   contrast in R3.5 without recommending a mount.
5. The round-2 observation about `public_eval_v1`'s differing evaluator hash
   inside the frozen baseline evidence is unchanged and was again left alone.
6. Commit status: **nothing staged, nothing committed.** The Trellis task
   remains at `review`.

---

# Round 4 (2026-09-10): head-camera proxy pair C5 and C6

**Headline.** Both round-4 conditions **passed all eight preflight stages** and
the **ten authorized runs `cam_c5_head_level_v1..v5` and
`cam_c6_head_down15_v1..v5` all completed with exit 0 and no timeout**. The
matrix now covers B0 plus six conditions, 30 executed `cam_*` runs, all exit 0.
All evidence is back at the local paths and the local manifest verifies
**2,211 / 2,211**.

Nothing was staged or committed. No model, evaluator, condition, protocol,
geometry, sign, or acceptance criterion was changed. No lead-authored file was
edited. No process the executor did not start was stopped or touched; the
resident `isaac-sim` container ran throughout. Round-1 to round-3 evidence was
deleted on neither side.

## R4.1 Sync Gate in (round-4 step 1) — PASSED

```bash
# local, from EXP
rsync -av --exclude '.DS_Store' --exclude '._*' --exclude '__pycache__' \
  public_scenes/requests/2026-09-10_lite3_camera_ablation/ \
  rented4090:/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090/public_scenes/requests/2026-09-10_lite3_camera_ablation/
rsync -av --exclude '._*' \
  public_scenes/configs/vln_cam_c1_lite3_rig.yaml \
  public_scenes/configs/vln_cam_c2_height_only.yaml \
  public_scenes/configs/vln_cam_c3_fov_only.yaml \
  public_scenes/configs/vln_cam_c4_raised_mount.yaml \
  public_scenes/configs/vln_cam_c5_head_level.yaml \
  public_scenes/configs/vln_cam_c6_head_down15.yaml \
  public_scenes/configs/habitat_dual_system_cam_cfg.py \
  rented4090:/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090/public_scenes/configs/

# remote, from the EXP root
sha256sum -c public_scenes/requests/2026-09-10_lite3_camera_ablation/authored_files.sha256
sha256sum work/InternNav/internnav/habitat_extensions/vln/habitat_vln_evaluator.py
```

- `authored_files.sha256`: **17 of 17 lines OK**, exit 0 on the remote (also
  verified locally with `shasum -a 256 -c` before the push: 17 of 17 OK).
- Remote worktree evaluator hash still
  `a05268d5e4fac8ab6147d2c828e16ae76d413fe074d2e7f0f99e26ae6fcbf3e7`,
  equal to the pinned baseline.
- Files changed on the push: the lead's round-4 revisions to `conditions.json`,
  `run_matrix.sh`, `authored_files.sha256`, `request.json`, `provenance.json`,
  `record_provenance.py`, `yaml_diffs.json`, `local_validation.txt`,
  `OPUS_EXECUTION_PACKAGE.md`, `RESULT.md`, `matrix_driver_round4.sh`,
  `review/LEAD_REVIEW.md`, and the two new YAMLs
  `vln_cam_c5_head_level.yaml`, `vln_cam_c6_head_down15.yaml`. The four
  round-1..3 YAMLs and the eval config were byte-identical on both sides but
  are re-listed by rsync because their mtimes moved.
- Nothing was deleted on either side; no `--delete` was used in either
  direction. Before the run the remote held exactly the twenty round-1..3
  directories and **no `cam_c5_*` or `cam_c6_*` path** under either
  `public_scenes/runs/` or `runs/`, so no run id was reused.
- `__pycache__` was excluded in both directions; the remote request directory
  contains no `.pyc` (verified before and after the manifest).

## R4.2 Resource check (round-4 step 2) — PASSED, no waiting needed

`REQ/preflight/resources_before_round4.txt` (2026-09-10T15:34:52Z).

| Item | Value |
| --- | --- |
| Device | NVIDIA GeForce RTX 4090, 24,564 MiB, driver 575.57.08, CUDA 12.9 |
| Used before the matrix | 2,903 MiB |
| **Free before the matrix** | **21,179 MiB** |
| GPU utilisation at the snapshot | 22 % |
| Resident GPU process | PID 1251 `/isaac-sim/kit/kit`, 2,859 MiB, untouched |
| Host | 62 GB RAM (57 GB available), 41 GB free on `/` |

Free memory equalled rounds 1-3 exactly, so no waiting was needed. Peak device
memory during the ten runs: **22,385 MiB** over 296 samples, i.e. about
19,482 MiB of evaluator on top of the resident Isaac Sim — the same footprint
as every earlier round. No CUDA out-of-memory occurred (0 of 10 stderr logs
contain "CUDA out of memory"); the two-consecutive-OOM stop rule was never
approached. The ten run directories consumed about 456 MB. `docker ps` is
recorded as "permission denied" for the `ubuntu` account, as in earlier rounds;
the Isaac Sim container was observed through `ps` and `nvidia-smi` only and was
never signalled.

## R4.3 Preflight (round-4 step 3) — C5 and C6 both **ALL_STAGES_PASSED**

```bash
cd /home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
bash public_scenes/scripts/link_launch_dir.sh
cd work/InternNav
mkdir -p public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight
for c in c5_head_level c6_head_down15; do
  CAM_YAML=public_scenes/configs/vln_cam_$c.yaml \
    ../../official_r2r/official_env_024/bin/python \
    public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight_cam.py --cond $c \
    2>&1 | tee public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight/${c}_stdout.txt
done
```

Run unattended through `REQ/preflight/run_preflight_round4.sh` (Deviation
R4-D1) from 2026-09-10T15:35:37Z; python exit 0 for both conditions.
`link_launch_dir.sh` reported `LAUNCH_LINKS_DONE` with all seven paths OK
(`REQ/preflight/link_launch_dir_round4.txt`).

All eight stages PASS for both, `all_stages_passed: true`,
`first_blocker: null`:

| # | Stage | C5 | C6 |
| --- | --- | --- | --- |
| 0 | official env versions | PASS | PASS |
| 1 | all paths resolve from the launch directory | PASS | PASS |
| 2 | pinned inputs match baseline `public_eval_v5` | PASS | PASS |
| 3 | condition eval config loads with `CAM_YAML` | PASS | PASS |
| 4 | condition habitat config composes to the specified geometry | PASS | PASS |
| 5 | start frame renders with the specified height, pitch, and floor distance | **PASS** | **PASS** |
| 6 | `look_down`/`look_up` behave per `tilt_angle` | **PASS** | **PASS** |
| 7 | GPU budget against the baseline footprint | PASS | PASS |

Stage 0 for both: habitat-lab 0.2.4, habitat-baselines 0.2.4, habitat-sim
0.3.3, torch 2.6.0+cu124, python 3.9.23, transformers 4.51.0, diffusers 0.32.2,
CUDA on an RTX 4090.

### R4.3.1 Stage 5 — measured sensor state and floor geometry

Episode 1, scene `skokloster-castle.glb`, start position
`[-1.967646837234497, 0.20027944445610046, 12.827132225036621]`, 640x480,
vfov 63.453 deg from hfov 79 — the same start pose used in every earlier round.

| Quantity | C5 measured | C6 measured | Specified | Verdict |
| --- | --- | --- | --- | --- |
| Sensor height above agent | **0.4000 m** | **0.4000 m** | 0.40 m | exact |
| Sensor forward offset | **0.2700 m** | **0.2700 m** | 0.27 m | exact |
| Sensor pitch down | **-0.0 deg** | **15.000 deg** | 0 / 15 deg | exact, sign included |
| Floor z-depth p90, bottom 16 rows | 0.961 m | 0.680 m | expectation 0.689 / 0.488 m | ratio 1.3961 / 1.3947 |
| **Implied agent-origin-to-floor gap** | **0.1584 m** | **0.1579 m** | bounds [-0.05, 0.30] m | **both inside** |

Reference values also recorded: `reference_ground_distance_m_h_over_tan`
0.647 m (C5) and 0.377 m (C6); top-row median depth 8.134 m and 7.390 m. The
two implied gaps agree with the 0.158-0.163 m range measured for C1-C4 in the
earlier rounds at the same start pose, which is the navmesh property the lead's
revised criterion was written against; they match the package's "about 0.16 m"
expectation.

### R4.3.2 Stage 6 — the tilt no-op check (`tilt_angle: 0` for both)

| Quantity | C5 | C6 | Limit (`conditions.json`) | Verdict |
| --- | --- | --- | --- | --- |
| `pitch_delta_deg_after_look_down` | **0.0** | **0.0** | `tilt_noop_max_pitch_delta_deg` 0.01 | **both inside** |
| `changed_pixel_fraction_after_look_down` | **0.0** | **0.0** | `tilt_noop_max_changed_pixel_fraction` 0.01 | **both inside** |
| `frame_identical_after_look_down` | true | true | not a criterion | recorded only |
| `mean_abs_channel_delta_after_look_down` | 0.0 | 0.0 | — | recorded only |
| pitch before / after look_down / after look_up | -0.0 / -0.0 / -0.0 | 15.0 / 15.0 / 15.0 | — | restored |

Observation offered to the lead, **not acted on**: the package expected "about
0.003" for the changed-pixel fraction, from C1's round-3 measurement. C5 and C6
measured exactly **0.0** — the zero-amount `look_down` left the frame
bit-identical, so the 1-2 ULP quaternion re-normalisation that C1 showed did
not occur for these two orientations. Both numbers are inside the lead's
bounds, so the criterion was met either way; no criterion was touched.

Stage 7 for both: free 21,163 MiB against a required 19,478 MiB, margin
1,685 MiB, resident compute app `1251, /isaac-sim/kit/kit, 2859 MiB` recorded
and untouched.

Four PNGs were written for lead inspection:
`REQ/preflight/c5_head_level_start_rgb.png`,
`c5_head_level_start_depth_mm.png`, `c6_head_down15_start_rgb.png`,
`c6_head_down15_start_depth_mm.png`. No earlier round's PNG was overwritten.

## R4.4 Matrix (round-4 step 4) — 10 runs, all exit 0, no timeouts

```bash
cd /home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
nohup bash public_scenes/requests/2026-09-10_lite3_camera_ablation/matrix_driver_round4.sh \
  c5_head_level c6_head_down15 \
  > public_scenes/requests/2026-09-10_lite3_camera_ablation/matrix_driver_round4_stdout.txt 2>&1 &
```

The lead-authored `matrix_driver_round4.sh` was used unchanged; it runs the
package's `run_matrix.sh c5_head_level c6_head_down15` and appends to
`matrix_stdout.txt`. The preflight gate in `run_matrix.sh` passed for both
conditions, and no `cam_c5_*` or `cam_c6_*` run id existed.

`REQ/matrix_log.jsonl`, the ten new lines (rounds 1-3 lines 1-20 unchanged;
the file now has 30 lines):

| Run id | Condition | exit_code | timed_out | wall s | deadline s |
| --- | --- | --- | --- | --- | --- |
| cam_c5_head_level_v1 | c5_head_level | 0 | false | 127.6 | 1800 |
| cam_c5_head_level_v2 | c5_head_level | 0 | false | 122.4 | 1800 |
| cam_c5_head_level_v3 | c5_head_level | 0 | false | 122.1 | 1800 |
| cam_c5_head_level_v4 | c5_head_level | 0 | false | 173.0 | 1800 |
| cam_c5_head_level_v5 | c5_head_level | 0 | false | 150.8 | 1800 |
| cam_c6_head_down15_v1 | c6_head_down15 | 0 | false | 129.8 | 1800 |
| cam_c6_head_down15_v2 | c6_head_down15 | 0 | false | 150.3 | 1800 |
| cam_c6_head_down15_v3 | c6_head_down15 | 0 | false | 165.5 | 1800 |
| cam_c6_head_down15_v4 | c6_head_down15 | 0 | false | 159.7 | 1800 |
| cam_c6_head_down15_v5 | c6_head_down15 | 0 | false | 188.9 | 1800 |

- Matrix wall time 2026-09-10T15:36:47Z to 16:01:47Z, about **25 minutes**;
  slowest run 188.9 s, 10.5 percent of its 1,800 s deadline. Both conditions
  run at roughly C2's speed, far below C1's.
- **Authorized-run budget: 30 authorized in total (20 in rounds 1-3, 10 more
  for round 4); 10 used in round 4 — 30 of 30 used, 0 remaining.**
- Ten directories `public_scenes/runs/cam_c5_head_level_v{1..5}` and
  `cam_c6_head_down15_v{1..5}`, each with `progress.json` carrying **two**
  episode records (verified 10 of 10), plus `inputs.json`, `result.json`,
  `exit.json` (all `exit_code: 0`), `environment.json`,
  `gpu_samples_every_5s.csv`, `trace_0/`, `vis_0/`, `vis_debug/`,
  `check_sim_0/`.
- Ten supervisor records `runs/cam_c5_head_level_v{1..5}` and
  `runs/cam_c6_head_down15_v{1..5}` with `meta.json`, `stdout.log`,
  `stderr.log`, `process.json`; every `meta.json` reads
  `exit_code: 0, timed_out: false`.
- No run was deleted or rerun under an existing id; no OOM.
- Input identity: all ten runs record SHA-256 **identical to
  `public_eval_v5`** for the six shared inputs — `scripts/eval/eval.py`, the
  evaluator, `internnav/model/utils/vln_utils.py`, the scene `.glb`, the
  `.navmesh`, and the frozen `val_unseen.json.gz` — **0 mismatches**. The only
  differing input keys are the condition's own config files
  (`habitat_dual_system_cam_cfg.py`, the condition YAML, `conditions.json`),
  which differ by design.
- `evaluator_sha256_set` for C5 and for C6 is the single pinned `a05268d5...`.

## R4.5 Summary and media checks (round-4 step 5) — PASSED

```bash
official_r2r/official_env_024/bin/python \
  public_scenes/requests/2026-09-10_lite3_camera_ablation/summarise_conditions.py
PATH=.../official_r2r/official_env_024/bin:$PATH python3 REQ/ffprobe_round3.py
```

- **B0 gate holds: the summariser again reproduced the recorded baseline
  exactly — episode 1 3/5, episode 2 2/5.** The C1-C4 rows are unchanged from
  round 3.
- **120 MP4s probed over all 30 `cam_*` runs, 0 decode errors** (rounds 1-3's
  80 plus 40 new).
- **59 of 60 `vis_debug` videos have a frame count equal to the `steps` value
  in `progress.json`; all 20 round-4 videos match exactly.** The single
  exception is the already-recorded round-3 anomaly on
  `cam_c1_lite3_rig_v1` episode 2 (502 frames against 501 steps, the only
  step-capped episode in the matrix); it is unchanged and was not touched.

### `condition_summary.md` (all conditions, regenerated over 60 runs)

| Condition | Height | Pitch | HFOV | Tilt | Ep1 success | Ep1 NE m (min/med/max) | Ep2 success | Ep2 NE m (min/med/max) | Ep2 collisions (min/med/max) | Learned STOP | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 baseline (recorded) | 1.25 m | 0 deg | 79 | 15 | 3/5 | 1.05/1.252/4.057 | 2/5 | 2.154/4.892/5.911 | 8/10/10 | 10/10 | 5/10 |
| c1_lite3_rig (Lite3 rig faithful) | 0.42 m | 20 deg | 54 | 0 | 1/5 | 1.063/12.184/16.941 | 0/5 | 4.267/11.996/14.788 | 9/15/83 | 9/10 | 1/10 |
| c2_height_only (Height only) | 0.42 m | 0 deg | 79 | 15 | 3/5 | 1.26/1.415/4.677 | 2/5 | 2.88/3.059/8.467 | 7/13/19 | 10/10 | 5/10 |
| c3_fov_only (FOV only) | 1.25 m | 0 deg | 54 | 15 | 2/5 | 1.208/13.877/16.3 | 1/5 | 2.488/5.424/9.045 | 2/4/4 | 10/10 | 3/10 |
| c4_raised_mount (Raised mount candidate) | 0.65 m | 15 deg | 54 | 0 | 2/5 | 0.785/14.45/16.901 | 0/5 | 4.505/8.931/10.202 | 17/40/58 | 10/10 | 2/10 |
| **c5_head_level (Head camera proxy, level)** | **0.4 m** | **0 deg** | **79** | **0** | **1/5** | 1.944/4.694/7.855 | **1/5** | 2.71/5.128/8.611 | 7/11/16 | 10/10 | **2/10** |
| **c6_head_down15 (Head camera proxy, 15 deg down)** | **0.4 m** | **15 deg** | **79** | **0** | **5/5** | 0.497/0.66/0.727 | **0/5** | 3.461/5.838/8.359 | 18/30/45 | 10/10 | **5/10** |

Supporting detail for the two new conditions (executor transcription from
`condition_summary.json`; the lead recomputes from `progress.json` and the
traces per AC4):

| Condition / episode | Success | Oracle success | Entered radius | Learned STOP | Steps min/med/max | Collisions min/med/max | S2 level_view / look_down_followup | Pixel goals min/med/max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 ep1 | 3/5 | 3 | 3 | 5/5 | 63/80/81 | 0/0/0 | 53 / 37 | 6/8/8 |
| B0 ep2 | 2/5 | 5 | 5 | 5/5 | 86/107/116 | 8/10/10 | 66 / 55 | 9/12/12 |
| **C5 ep1** | **1/5** | 1 | 1 | 5/5 | 61/77/82 | 0/0/0 | 56 / 39 | 6/8/10 |
| **C5 ep2** | **1/5** | 5 | 5 | 5/5 | 101/113/171 | 7/11/16 | 83 / 65 | 12/12/16 |
| **C6 ep1** | **5/5** | 5 | 5 | 5/5 | 64/69/72 | 0/0/0 | 50 / 35 | 7/7/7 |
| **C6 ep2** | **0/5** | 5 | 5 | 5/5 | 119/165/219 | 18/30/45 | 107 / 87 | 13/18/22 |

Per-run outcome (episode_id, success, steps, navigation error m, oracle
success, SPL):

- **C5** v1 (1, 1.0, 71, 1.944, os 1, spl 1.0) (2, 0.0, 111, 4.795, os 1,
  spl 0.0); v2 (1, 0.0, 77, 4.694, os 0, spl 0.0) (2, 1.0, 101, 2.710, os 1,
  spl 0.817); v3 (1, 0.0, 61, 4.152, os 0, spl 0.0) (2, 0.0, 113, 5.128, os 1,
  spl 0.0); v4 (1, 0.0, 80, 7.855, os 0, spl 0.0) (2, 0.0, 171, 8.611, os 1,
  spl 0.0); v5 (1, 0.0, 82, 4.963, os 0, spl 0.0) (2, 0.0, 120, 6.728, os 1,
  spl 0.0).
- **C6** v1 (1, 1.0, 70, 0.727, os 1, spl 1.0) (2, 0.0, 119, 3.461, os 1,
  spl 0.0); v2 (1, 1.0, 69, 0.654, os 1, spl 1.0) (2, 0.0, 147, 5.838, os 1,
  spl 0.0); v3 (1, 1.0, 72, 0.497, os 1, spl 1.0) (2, 0.0, 175, 4.919, os 1,
  spl 0.0); v4 (1, 1.0, 64, 0.660, os 1, spl 1.0) (2, 0.0, 165, 8.359, os 1,
  spl 0.0); v5 (1, 1.0, 67, 0.688, os 1, spl 1.0) (2, 0.0, 219, 8.356, os 1,
  spl 0.0).

Termination reasons: `habitat_episode_over` 5/5 for every episode of both
conditions — every one of the twenty round-4 episodes ended on a learned
System-2 STOP, and no round-4 episode reached the 500-step evaluator cap.

Non-terminal stop events: C5 ep1 `forward_budget_exhausted` 32 /
`s1_stop_mid_segment` 7, ep2 57 / 8; C6 ep1 30 / 5, ep2 83 / 4.

Stated descriptively, with attribution to System 1 or System 2 outside this
test's claim boundary: on these two frozen episodes the head-camera proxy with
a 15-degree downward pitch (C6) reaches **5 of 10** successful episodes, equal
to B0 and C2 and the joint best of the six conditions, and it is the **only
configuration in the whole matrix that succeeds on episode 1 in all five
runs** (5/5 against B0's 3/5), with a navigation error between 0.497 m and
0.727 m and SPL 1.0 every time. Its episode 2 never succeeds (0/5) although all
five runs entered the goal radius and achieved oracle success, and it carries
the second-highest episode-2 collision count in the matrix (18/30/45). The
level variant at the same height and FOV (C5) reaches only 2 of 10 with a much
wider episode-1 error spread, so on this test the difference between the pair
is the 15-degree pitch and not the 0.40 m height. Two frozen episodes and five
unseeded runs are not enough to rank conditions statistically; this is a
functional signal, not a benchmark result, and the C5/C6 geometry is the
lead's estimate pending the on-robot measurement.

## R4.6 Manifest and Sync Gate out (round-4 step 6) — PASSED

```bash
# remote, from the EXP root, after the last evidence edit
find public_scenes/runs/cam_* runs/cam_* public_scenes/requests/2026-09-10_lite3_camera_ablation -type f \
  ! -name manifest.sha256 ! -name OPUS_RETURN.md -print0 | sort -z | xargs -0 sha256sum \
  > public_scenes/requests/2026-09-10_lite3_camera_ablation/manifest.sha256

# local, from the EXP root
rsync -a "rented4090:.../public_scenes/runs/cam_c5_*" "rented4090:.../public_scenes/runs/cam_c6_*" public_scenes/runs/
rsync -a "rented4090:.../runs/cam_c5_*" "rented4090:.../runs/cam_c6_*" runs/
rsync -a --exclude '__pycache__' rented4090:.../public_scenes/requests/2026-09-10_lite3_camera_ablation/ \
         public_scenes/requests/2026-09-10_lite3_camera_ablation/
shasum -a 256 -c public_scenes/requests/2026-09-10_lite3_camera_ablation/manifest.sha256
```

- Manifest: **2,211 files** (round 1: 787; round 2: 1,091; round 3: 1,571),
  covering all thirty `cam_*` run directories, all thirty supervisor records,
  and the whole request directory. Remote self-verification: 0 non-OK lines.
- **Local verification: 2,211 of 2,211 lines OK, 0 FAILED, exit 0.**
- Transferred back: 582 files / 476,288,657 bytes of run evidence, 40 files /
  1,501,452 bytes of supervisor records, 21 files / 1,586,852 bytes of request
  files. No `--delete` in either direction; no local file was removed.

Returned local paths (all under `EXP`), new in round 4:

- `public_scenes/runs/cam_c5_head_level_v{1..5}/`,
  `public_scenes/runs/cam_c6_head_down15_v{1..5}/`
- `runs/cam_c5_head_level_v{1..5}/`, `runs/cam_c6_head_down15_v{1..5}/`
- `public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight/`:
  `c5_head_level.json`, `c5_head_level_start_rgb.png`,
  `c5_head_level_start_depth_mm.png`, `c5_head_level_stdout.txt`,
  `c6_head_down15.json`, `c6_head_down15_start_rgb.png`,
  `c6_head_down15_start_depth_mm.png`, `c6_head_down15_stdout.txt`,
  `resources_before_round4.txt`, `link_launch_dir_round4.txt`,
  `preflight_round4_stdout.txt`, `run_preflight_round4.sh`
- `public_scenes/requests/2026-09-10_lite3_camera_ablation/`:
  `matrix_driver_round4_stdout.txt`, `summarise_round4_stdout.txt`,
  `ffprobe_round4_stdout.txt`, updated `matrix_log.jsonl` (30 lines),
  `matrix_log.jsonl.txt`, `matrix_stdout.txt`, `condition_summary.json`,
  `condition_summary.md`, `ffprobe_frame_counts.json`, `manifest.sha256`, and
  this `OPUS_RETURN.md`

`OPUS_RETURN.md` was written after the manifest, is deliberately excluded from
it, and was copied to the remote afterwards. Round-1 to round-3 files were
preserved on both sides, including `preflight/round1_failed_ratio_criterion/`
and `preflight/round2_c1_stage6_blocked/`.

## R4.7 Deviations from the round-4 package steps

- **R4-D1 — Unattended preflight driver.** As in rounds 1-3, the executor's
  per-command timeout is shorter than the preflight, so the package's round-1
  step-3 command block was placed verbatim in a new owned-path helper script,
  `REQ/preflight/run_preflight_round4.sh`, and started with `setsid nohup ... &`.
  A new file rather than an edit to the round-1/2/3 helpers, so earlier
  evidence stays byte-identical. Only the condition list is narrowed, per the
  package's round-4 step 3. The lead-authored `matrix_driver_round4.sh` was
  used unchanged for step 4.
- **R4-D2 — ffprobe path and script reuse.** Unchanged from round-1 D3 /
  R2-D4 / R3-D2: bare `ffprobe` is not on the remote default PATH, so
  `official_r2r/official_env_024/bin` was prepended. The package's step-5
  ffprobe block was not retyped; the byte-identical round-3 copy
  `REQ/ffprobe_round3.py` was executed unchanged (it globs all `cam_*` runs, so
  it covers round 4), and its stdout is at `REQ/ffprobe_round4_stdout.txt`.
- **R4-D3 — Summariser run detached.** For the same timeout reason the
  summariser was started with `setsid nohup` and its output captured to
  `REQ/summarise_round4_stdout.txt` instead of the terminal. The command is the
  package's, unchanged.
- **R4-D4 — `__pycache__` excluded from rsync.** Unchanged from R2-D5. The
  remote request directory contains no `.pyc` (verified before the manifest).

No other deviation. `conditions.json`, the six condition YAMLs, the eval
config, the preflight, the launcher, the matrix runner, the round-4 driver, and
the summariser were executed exactly as authored and hash-verified on the
remote before use. No lead-authored file was edited. No geometry, sign,
criterion, or evaluator logic was touched in this round.

## R4.8 Remaining issues and what the lead must decide

1. **Stage 6 measured 0.0, not the expected "about 0.003".** For both C5 and
   C6 the zero-amount `look_down` left the frame bit-identical and the pitch
   delta exactly 0.0, where C1 showed a 0.31 percent changed-pixel fraction
   from a 1-2 ULP quaternion re-normalisation. Both results are inside the
   lead's bounds and the criterion passed; the executor recorded the difference
   and changed nothing. Whether it is worth a note in the research record is
   the lead's call. Evidence: `REQ/preflight/c5_head_level.json`,
   `REQ/preflight/c6_head_down15.json`, stage 6 detail.
2. **The round-3 frame-count anomaly is unchanged.**
   `cam_c1_lite3_rig_v1` episode 2 still has 502 `vis_debug` frames against
   501 steps, the only mismatch among 60 videos and the only step-capped
   episode in the matrix. It was neither touched nor rerun. The criterion
   question raised in R3.8 item 1 is still open and still belongs to the lead.
3. **C6 outperforms the baseline on episode 1 and matches it overall.** C6
   reaches 5/5 on episode 1 where B0 reaches 3/5, and 5/10 in total, equal to
   B0 and C2. The executor states the numbers and the C5-versus-C6 contrast in
   R4.5 without recommending a mount or a pitch; that judgement, and whether
   two frozen episodes justify it, is the lead's.
4. **The C5/C6 geometry is an estimate.** `conditions.json` labels both
   conditions `geometry_status: "estimated; to be replaced by the on-robot
   measurement (checkerboard, IMU, tape)"`. Any conclusion about the deployment
   head camera inherits that status until the measurement is taken.
5. **The authorized run budget is now fully consumed**: 30 of 30 (20 in
   rounds 1-3, 10 in round 4). Any further run needs new authorization from
   Dr Sun.
6. The round-2 observation about `public_eval_v1`'s differing evaluator hash
   inside the frozen baseline evidence is unchanged and was again left alone.
7. Commit status: **nothing staged, nothing committed.** No git command was run
   in the local repository. The Trellis task remains at `review`.

# Round 5 (2026-09-11): fused virtual camera C7 executed, C8 blocked by the fusion-cost gate

**Headline.** `c7_fused_level` **passed all nine preflight stages** and its
**five authorized runs `cam_c7_fused_level_v1..v5` all completed with exit 0
and no timeout**. `c8_fused_level_720` **failed preflight stage 8 only**
(`fusion 226.47 ms/frame > 200.0`), so `run_matrix.sh`'s preflight gate skipped
it and **no C8 run was launched**; five of the ten authorized round-5 runs are
unused. Every geometric, coverage and image-fidelity stage passed for **both**
conditions. The matrix now covers B0 plus seven executed conditions, 35
executed `cam_*` runs, all exit 0. All evidence is back at the local paths and
the local manifest verifies **2,524 / 2,524**.

Nothing was staged or committed. No model, evaluator, plugin, fusion module,
preflight, condition, protocol, geometry or acceptance criterion was changed.
No lead-authored file was edited. No process the executor did not start was
stopped or touched; the resident `isaac-sim` container ran throughout.
Round-1 to round-4 evidence was deleted on neither side.

All ssh and rsync went through the lab jump host as the package's round-5
connectivity note requires (`-J gpu40901`); the direct alias was not used.

## R5.1 Sync Gate in (round-5 step 1) — PASSED

```bash
# local, from EXP
shasum -a 256 -c public_scenes/requests/2026-09-10_lite3_camera_ablation/authored_files.sha256
rsync -av -e 'ssh -o BatchMode=yes -o ConnectTimeout=25 -J gpu40901' \
  --exclude '.DS_Store' --exclude '._*' --exclude '__pycache__' \
  public_scenes/requests/2026-09-10_lite3_camera_ablation/ \
  rented4090:/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090/public_scenes/requests/2026-09-10_lite3_camera_ablation/
rsync -av -e 'ssh -o BatchMode=yes -o ConnectTimeout=25 -J gpu40901' --exclude '._*' \
  public_scenes/configs/habitat_dual_system_cam_cfg.py \
  public_scenes/configs/habitat_dual_system_fused_cfg.py \
  public_scenes/configs/vln_cam_c1_lite3_rig.yaml \
  public_scenes/configs/vln_cam_c2_height_only.yaml \
  public_scenes/configs/vln_cam_c3_fov_only.yaml \
  public_scenes/configs/vln_cam_c4_raised_mount.yaml \
  public_scenes/configs/vln_cam_c5_head_level.yaml \
  public_scenes/configs/vln_cam_c6_head_down15.yaml \
  public_scenes/configs/vln_cam_c7_fused_level.yaml \
  public_scenes/configs/vln_cam_c8_fused_level_720.yaml \
  rented4090:/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090/public_scenes/configs/

# remote, from the EXP root, then from the launch directory
bash public_scenes/scripts/link_launch_dir.sh
sha256sum -c public_scenes/requests/2026-09-10_lite3_camera_ablation/authored_files.sha256
sha256sum internnav/habitat_extensions/vln/habitat_vln_evaluator.py
```

- `authored_files.sha256`: **26 of 26 lines OK**, exit 0 on the remote (also
  verified locally with `shasum -a 256 -c` before the push: 26 of 26 OK).
- Remote worktree evaluator hash still
  `a05268d5e4fac8ab6147d2c828e16ae76d413fe074d2e7f0f99e26ae6fcbf3e7`,
  equal to the pinned baseline; the summariser later confirmed every C7 run's
  `inputs.json` carries the same value (`evaluator_sha256_set` has one element).
- Files changed on the push: the lead's round-5 additions and revisions
  `conditions.json`, `OPUS_EXECUTION_PACKAGE.md`, `RESULT.md`,
  `authored_files.sha256`, `fused_camera.py`, `fused_camera_plugin.py`,
  `test_fused_camera.py`, `make_fused_yamls.py`, `yaml_diffs_fused.json`,
  `preflight_fused.py`, `local_validation.txt`, `provenance.json`,
  `record_provenance.py`, `request.json`, `run_cam_eval.sh`,
  `matrix_driver_round5.sh`, `preflight/run_preflight_round5.sh`,
  `review/LEAD_REVIEW.md`, and the three new config files
  `habitat_dual_system_fused_cfg.py`, `vln_cam_c7_fused_level.yaml`,
  `vln_cam_c8_fused_level_720.yaml`. The seven round-1..4 YAMLs and
  `habitat_dual_system_cam_cfg.py` were byte-identical on both sides.
- `link_launch_dir.sh` reported `LAUNCH_LINKS_DONE` with all seven links `OK`
  (`preflight/link_launch_dir_round5.txt`).
- Nothing was deleted on either side; no `--delete` was used in either
  direction. Before the run the remote held exactly the thirty round-1..4
  directories and **no `cam_c7_*` or `cam_c8_*` path** under either
  `public_scenes/runs/` or `runs/`, so no run id was reused.

## R5.2 Resource check (round-5 step 2) — PASSED, no waiting needed

`REQ/preflight/resources_before_round5.txt` (2026-09-11T06:36:47Z). The
instance had been rebooted before dispatch (`uptime` 5 min), so the resident
processes were re-recorded as the package's round-5 note requires.

| Item | Value |
| --- | --- |
| Device | NVIDIA GeForce RTX 4090, 24,564 MiB, driver 575.57.08, CUDA 12.9 |
| Used before the matrix | 3,005 MiB |
| **Free before the matrix** | **21,077 MiB** |
| GPU utilisation at the snapshot | 23 % |
| Resident GPU process | PID **1267** `/isaac-sim/kit/kit`, 2,961 MiB, untouched |
| Host | 62 GB RAM (57 GB available), 41 GB free on `/` (80 % used) |

The isaac-sim container came back after the reboot under a new PID (1267,
rounds 1-4 saw PID 1251) and was recorded through `ps` and `nvidia-smi` only;
it was never signalled. `docker ps` is again "permission denied" for the
`ubuntu` account. Free memory (21,077 MiB) exceeded the baseline footprint of
19,478 MiB, so no waiting branch was entered.

GPU peak per run, whole device, from each run's `gpu_samples_every_5s.csv`
(minimum sample 3,005 MiB in every run, i.e. the resident Isaac Sim):

| Run | Peak used (MiB) | Samples | Implied evaluator footprint (MiB) |
| --- | --- | --- | --- |
| cam_c7_fused_level_v1 | 22,500 | 66 | 19,495 |
| cam_c7_fused_level_v2 | 22,496 | 54 | 19,491 |
| cam_c7_fused_level_v3 | 22,500 | 60 | 19,495 |
| cam_c7_fused_level_v4 | 22,496 | 56 | 19,491 |
| cam_c7_fused_level_v5 | 22,500 | 55 | 19,495 |

The same footprint as every earlier round (rounds 1-4 peaked at 22,385 MiB with
a 2,859 MiB resident container). **0 of 5** stderr logs contain
"CUDA out of memory"; the two-consecutive-OOM stop rule was never approached.

## R5.3 Preflight (round-5 step 3) — C7 **ALL_STAGES_PASSED**, C8 failed stage 8 only

```bash
# remote, from the EXP root
setsid nohup bash public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight/run_preflight_round5.sh \
  > public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight/run_preflight_round5_stdout.txt 2>&1 &
```

Started 2026-09-11T06:37:05Z, `PREFLIGHT_DRIVER_DONE` by 06:37:30Z.
Python exit 0 for C7, exit 1 for C8.

### Stage verdicts

| # | Stage | C7 | C8 |
| --- | --- | --- | --- |
| 1 | official env versions | PASS | PASS |
| 2 | all paths resolve from the launch directory | PASS | PASS |
| 3 | pinned inputs match baseline `public_eval_v5` | PASS | PASS |
| 4 | fused eval config loads with `CAM_YAML` and registers the plugin sensors | PASS | PASS |
| 5 | condition habitat config composes to the specified geometry | PASS | PASS |
| 6 | start frame: fused rgb overrides sim rgb, matches the ideal render, sensors sit where configured | PASS | PASS |
| 7 | `look_down` is a no-op for the fused rgb (tilt_angle 0) | PASS | PASS |
| 8 | fusion cost per frame | PASS | **FAIL** |
| 9 | free GPU memory after closing the preflight simulator | PASS | not attempted |

Stage 9 for C8 is recorded `ok: false, skipped: true, detail: "not attempted:
an earlier stage failed"` — it is a consequence of stage 8, not a second
independent failure.

### Stage 6 numbers (the fusion correctness stage), both conditions

| Quantity | C7 (`d435` 640x480, HFOV 55) | C8 (`d435` 1280x720, HFOV 69) | Expected |
| --- | --- | --- | --- |
| `fused_equals_offline_recompute` | **true** | **true** | true |
| `fraction_of_pixels_differing_from_ideal` | 0.7106 | 0.7029 | well above 0.01 |
| coverage `head` | 0.77613 | 0.77259 | about 0.78 |
| coverage `d435` | 0.15236 | 0.20023 | - |
| coverage `blend` | 0.01137 | 0.01491 | 8 rows |
| **coverage `none`** | **0.06014** | **0.012272** | about 0.06 / 0.013 |
| head-region `mean_abs_err` (px) | **1.612** (PSNR 35.20 dB, 238,426 px) | **1.615** (PSNR 35.18 dB, 237,339 px) | below 10 |
| d435-region `mean_abs_err` (px) | 0.834 (PSNR 44.32 dB, 46,804 px) | 1.063 (PSNR 40.87 dB, 61,510 px) | below 20 |
| blend-region `mean_abs_err` (px) | 0.995 (PSNR 42.51 dB, 3,494 px) | 1.103 (PSNR 41.74 dB, 4,581 px) | - |

Every predicted coverage number was met: C7's uncovered fraction 6.014 percent
against the lead's "about 6 percent" and the 9 percent bound; C8's 1.2272
percent against "about 1.3 percent" and the 4 percent bound. Both conditions
reproduce the fused image bit-for-bit offline (`fused_equals_offline_recompute`
true), so the task sensor the evaluator reads is the fusion the lead designed.

### Measured sensor state (identical for both conditions, matching `conditions.json` exactly)

| Sensor | Height above agent (m) | `pitch_down_deg` | Forward offset (m) |
| --- | --- | --- | --- |
| `rgb` (fused virtual) | 0.40 | -0.0 | 0.27 |
| `depth` (ideal, for the evaluator) | 0.40 | -0.0 | 0.27 |
| `head_rgb` | 0.40 | **-16.7** | 0.27 |
| `d435_rgb` | 0.42 | **+20.0** | 0.25 |
| `d435_depth` | 0.42 | **+20.0** | 0.25 |

Every value equals the package's expectation (head `-16.7`, d435 `+20`, virtual
`0`, heights 0.40/0.42, forward offsets 0.27/0.25). Floor check for both:
measured bottom-row z-depth p90 0.961 m against an expected flat-floor 0.689 m,
**implied agent-origin-to-floor gap 0.1584 m**, inside the lead's
`floor_gap_bounds_m` [-0.05, 0.30] and equal to the 0.158-0.163 m seen in
rounds 1-4.

Stage 7 (tilt no-op): every sensor pitch unchanged to the printed precision for
both conditions; changed pixel fraction **0.000693** (C7) and **0.000856** (C8)
against the 0.05 bound the lead set for resampled fused pixels, mean absolute
channel delta 0.000291 and 0.000426.

### The C8 failure, verbatim

```
Traceback (most recent call last):
  File ".../public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight_fused.py", line 47, in stage
    entry['detail'] = fn()
  File ".../public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight_fused.py", line 395, in s_cost
    raise RuntimeError(f'fusion {res["fusion_ms_mean"]} ms/frame > {pff["max_fusion_ms_per_frame"]}')
RuntimeError: fusion 226.47 ms/frame > 200.0
```

Stage 8 times ten consecutive `sensor.fuse_from(obs)` calls on the start frame
and compares the mean with `conditions.json`
`preflight.fused.max_fusion_ms_per_frame` (200.0):

| Condition | `fusion_ms_mean` | `fusion_ms_max` | calls | bound | verdict |
| --- | --- | --- | --- | --- | --- |
| C7 | **135.70** | 180.34 | 10 | 200.0 | pass (margin 64.3 ms) |
| C8 | **226.47** | (stage raised) | 10 | 200.0 | **fail (over by 26.47 ms)** |

C8 reprojects a 1280x720 D435i colour+depth pair instead of 640x480 — 3x the
source pixels — which is the whole difference between the two conditions. The
stage-6 single-call figures show the same ordering (`fusion_ms_last_call`
190.32 ms for C7, 222.54 ms for C8). This is a throughput bound, not a
correctness one: every C8 geometry, coverage and fidelity stage passed, and its
uncovered fraction (1.23 percent) is the better of the two. Per the package the
executor did **not** edit the plugin, the fusion module, the preflight or
`conditions.json`, did not retry, and did not run C8.

Stage 9 for C7: device total 24,564 MiB, used 3,021, **free 21,061 MiB**,
required 19,478 MiB (max baseline footprint), **margin 1,583 MiB**; resident
compute app recorded as `1267, /isaac-sim/kit/kit, 2961 MiB` and never touched.

Artefacts returned for **both** conditions regardless of verdict, as the
package requires: `REQ/preflight/c7_fused_level.json`,
`c8_fused_level_720.json`, `<cond>_stdout.txt`, and seven PNGs each
(`_start_fused_rgb`, `_start_ideal_rgb`, `_start_head_rgb`, `_start_d435_rgb`,
`_start_d435_depth_mm`, `_start_depth_mm`, `_start_coverage`), plus
`run_preflight_round5_stdout.txt`, `link_launch_dir_round5.txt` and
`resources_before_round5.txt`.

## R5.4 Matrix (round-5 step 4) — 5 runs, all exit 0, no timeouts; C8 skipped by the gate

```bash
# remote, from the EXP root
setsid nohup bash public_scenes/requests/2026-09-10_lite3_camera_ablation/matrix_driver_round5.sh \
  c7_fused_level c8_fused_level_720 \
  > public_scenes/requests/2026-09-10_lite3_camera_ablation/matrix_driver_round5_stdout.txt 2>&1 &
```

Both conditions were passed to the lead-authored driver exactly as the
package's round-5 step 4 specifies. `run_matrix.sh` gates each condition on its
own preflight report, so C8 was refused before any run started:

```
SKIP condition c8_fused_level_720: preflight report did not pass all stages
```

Driver start 2026-09-11T06:39:55Z, `MATRIX_DONE` and `MATRIX_DRIVER_DONE rc=0`
at 2026-09-11T07:04:22Z; total wall about 24.5 minutes.

| Run id | Started (UTC) | Exit code | Timed out | Deadline (s) | Wall (s) |
| --- | --- | --- | --- | --- | --- |
| cam_c7_fused_level_v1 | 06:39:55 | 0 | false | 1800 | 332.4 |
| cam_c7_fused_level_v2 | 06:45:27 | 0 | false | 1800 | 272.3 |
| cam_c7_fused_level_v3 | 06:50:00 | 0 | false | 1800 | 302.7 |
| cam_c7_fused_level_v4 | 06:55:03 | 0 | false | 1800 | 283.5 |
| cam_c7_fused_level_v5 | 06:59:46 | 0 | false | 1800 | 275.4 |

The first C7 run exited 0, so the package's "stop the matrix if the first C7 run
exits non-zero" branch was not entered and nothing was killed. Five runs
consumed 5 of the 10 authorized round-5 runs; the 5 C8 runs are unused.
`REQ/matrix_log.jsonl` now has 35 lines (30 from rounds 1-4 plus these 5), every
one `exit_code: 0`, `timed_out: false`. No run id was rerun or deleted.

## R5.5 Summary and media checks (round-5 step 5) — PASSED

```bash
# remote, from the launch directory work/InternNav
../../official_r2r/official_env_024/bin/python \
  public_scenes/requests/2026-09-10_lite3_camera_ablation/summarise_conditions.py \
  > public_scenes/requests/2026-09-10_lite3_camera_ablation/summarise_round5_stdout.txt 2>&1
PATH=.../official_r2r/official_env_024/bin:$PATH python3 \
  public_scenes/requests/2026-09-10_lite3_camera_ablation/ffprobe_round3.py \
  > public_scenes/requests/2026-09-10_lite3_camera_ablation/ffprobe_round5_stdout.txt 2>&1
```

Both exit 0. `SUMMARY_WRITTEN` for `condition_summary.json` and
`condition_summary.md`.

- **B0 gate holds: the summariser again reproduced the recorded baseline
  exactly — episode 1 3/5, episode 2 2/5.** The C1-C6 rows are unchanged from
  round 4.
- **140 MP4s probed over all 35 `cam_*` runs, 0 decode errors** (rounds 1-4's
  120 plus 20 new).
- **All 10 C7 `vis_debug` frame counts equal the `steps` value in
  `progress.json`** (55/94, 65/104, 58/146, 60/125, 55/113). The one
  outstanding mismatch among the 70 `vis_debug` videos is still the recorded
  round-3 anomaly on `cam_c1_lite3_rig_v1` episode 2; it was not touched.
- `evaluator_sha256_set` for C7 is the single pinned value
  `a05268d5e4fac8ab6147d2c828e16ae76d413fe074d2e7f0f99e26ae6fcbf3e7`;
  `runs_without_progress_json` is empty.

### `condition_summary.md` (all conditions, regenerated over 70 runs)

| Condition | Height | Pitch | HFOV | Tilt | Ep1 success | Ep1 NE m (min/med/max) | Ep2 success | Ep2 NE m (min/med/max) | Ep2 collisions (min/med/max) | Learned STOP | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 baseline (recorded) | 1.25 m | 0 deg | 79 | 15 | 3/5 | 1.05/1.252/4.057 | 2/5 | 2.154/4.892/5.911 | 8/10/10 | 10/10 | 5/10 |
| c1_lite3_rig (Lite3 rig faithful) | 0.42 m | 20 deg | 54 | 0 | 1/5 | 1.063/12.184/16.941 | 0/5 | 4.267/11.996/14.788 | 9/15/83 | 9/10 | 1/10 |
| c2_height_only (Height only) | 0.42 m | 0 deg | 79 | 15 | 3/5 | 1.26/1.415/4.677 | 2/5 | 2.88/3.059/8.467 | 7/13/19 | 10/10 | 5/10 |
| c3_fov_only (FOV only) | 1.25 m | 0 deg | 54 | 15 | 2/5 | 1.208/13.877/16.3 | 1/5 | 2.488/5.424/9.045 | 2/4/4 | 10/10 | 3/10 |
| c4_raised_mount (Raised mount candidate) | 0.65 m | 15 deg | 54 | 0 | 2/5 | 0.785/14.45/16.901 | 0/5 | 4.505/8.931/10.202 | 17/40/58 | 10/10 | 2/10 |
| c5_head_level (Head camera proxy, level) | 0.4 m | 0 deg | 79 | 0 | 1/5 | 1.944/4.694/7.855 | 1/5 | 2.71/5.128/8.611 | 7/11/16 | 10/10 | 2/10 |
| c6_head_down15 (Head camera proxy, 15 deg down) | 0.4 m | 15 deg | 79 | 0 | 5/5 | 0.497/0.66/0.727 | 0/5 | 3.461/5.838/8.359 | 18/30/45 | 10/10 | 5/10 |
| **c7_fused_level (Fused virtual camera, level, D435i colour 640x480)** | **0.4 m** | **0 deg** | **79** | **0** | **0/5** | 7.068/7.453/7.94 | **0/5** | 3.097/7.577/7.743 | 4/13/19 | 10/10 | **0/10** |
| c8_fused_level_720 (Fused virtual camera, level, D435i colour 1280x720) | 0.4 m | 0 deg | 79 | 0 | 0/0 | - | 0/0 | - | - | 0/0 | **0/0 (not run)** |

The C8 row is a structural zero: the condition was never executed, and the
summariser prints `0/0` for a condition with no runs. It must not be read as a
C8 result.

Supporting detail for C7 (executor transcription from `condition_summary.json`;
the lead recomputes from `progress.json` and the traces per AC4):

| Condition / episode | Success | Oracle success | Entered radius | Learned STOP | Steps min/med/max | Collisions min/med/max | S2 level_view / look_down_followup | Pixel goals min/med/max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 ep1 | 3/5 | 3 | 3 | 5/5 | 63/80/81 | 0/0/0 | 53 / 37 | 6/8/8 |
| B0 ep2 | 2/5 | 5 | 5 | 5/5 | 86/107/116 | 8/10/10 | 66 / 55 | 9/12/12 |
| C5 ep1 | 1/5 | 1 | 1 | 5/5 | 61/77/82 | 0/0/0 | 56 / 39 | 6/8/10 |
| C5 ep2 | 1/5 | 5 | 5 | 5/5 | 101/113/171 | 7/11/16 | 83 / 65 | 12/12/16 |
| **C7 ep1** | **0/5** | **0** | **0** | 5/5 | 55/58/65 | 0/0/0 | 52 / 37 | 7/7/8 |
| **C7 ep2** | **0/5** | 5 | 5 | 5/5 | 94/113/146 | 4/13/19 | 83 / 61 | 11/12/15 |

Per-run outcome (episode_id, success, steps, navigation error m, oracle
success, SPL, collisions, minimum distance to goal m):

- **C7** v1 (1, 0.0, 55, 7.690, os 0, spl 0.0, coll 0, minD 7.615)
  (2, 0.0, 94, 3.097, os 1, spl 0.0, coll 13, minD 1.453);
  v2 (1, 0.0, 65, 7.453, os 0, spl 0.0, coll 0, minD 7.453)
  (2, 0.0, 104, 7.743, os 1, spl 0.0, coll 4, minD 1.191);
  v3 (1, 0.0, 58, 7.068, os 0, spl 0.0, coll 0, minD 7.068)
  (2, 0.0, 146, 7.734, os 1, spl 0.0, coll 18, minD 0.334);
  v4 (1, 0.0, 60, 7.940, os 0, spl 0.0, coll 0, minD 7.886)
  (2, 0.0, 125, 3.252, os 1, spl 0.0, coll 19, minD 1.497);
  v5 (1, 0.0, 55, 7.202, os 0, spl 0.0, coll 0, minD 7.202)
  (2, 0.0, 113, 7.577, os 1, spl 0.0, coll 7, minD 0.105).

Termination reasons: `habitat_episode_over` 5/5 for both episodes — **every one
of the ten C7 episodes ended on a learned System-2 STOP**, and no C7 episode
reached the 500-step evaluator cap. Non-terminal stop events: ep1
`forward_budget_exhausted` 21 / `s1_stop_mid_segment` 16; ep2 57 / 4.

Stated descriptively, with attribution to System 1, System 2 or the fusion
outside this test's claim boundary: on these two frozen episodes the fused
virtual camera scores **0 of 10**, the lowest in the matrix. Its virtual
geometry is identical to C5 (0.40 m, 0.27 m forward, level, HFOV 79, tilt 0),
which scores 2 of 10 from an ideal single render, so the measured difference
between the pair is the fusion itself and not the camera pose. Two features of
the C7 numbers are worth the lead's attention and are reported without
interpretation:

1. **Episode 1 never entered the goal radius in any of the five runs**
   (`n_entered_success_radius` 0, `n_oracle_success` 0). No other condition in
   the matrix, including C1 at 1/10 overall, has a zero oracle-success episode;
   every other condition's ep1 or ep2 reached the radius at least once. The
   five episode-1 navigation errors are tightly clustered (7.068-7.940 m,
   spread 0.87 m) with **zero collisions** and short episodes (55-65 steps),
   i.e. the agent consistently stopped early somewhere the other conditions do
   not.
2. **Episode 2 behaves like the rest of the matrix**: all five runs entered the
   radius and achieved oracle success, and none stopped at the right moment
   (minimum distance to goal down to 0.105 m in v5), so its failure mode is the
   familiar late/early STOP rather than a navigation breakdown.

Five unseeded runs on two frozen episodes are not enough to rank conditions
statistically; this is a functional signal, not a benchmark result. The head
pose and intrinsics are measured, but the head height/offset and the D435i pose
remain estimates (`geometry_status` in `conditions.json`).

## R5.6 Manifest and Sync Gate out (round-5 step 6) — PASSED

```bash
# remote, from the EXP root, after the last evidence edit
find public_scenes/runs/cam_* runs/cam_* public_scenes/requests/2026-09-10_lite3_camera_ablation -type f \
  ! -name manifest.sha256 ! -name OPUS_RETURN.md ! -path '*/__pycache__/*' -print0 | sort -z | xargs -0 sha256sum \
  > public_scenes/requests/2026-09-10_lite3_camera_ablation/manifest.sha256

# local, from the EXP root
rsync -a -e 'ssh ... -J gpu40901' "rented4090:.../public_scenes/runs/cam_c7_fused_level_v{1..5}" public_scenes/runs/
rsync -a -e 'ssh ... -J gpu40901' "rented4090:.../runs/cam_c7_fused_level_v{1..5}" runs/
rsync -a -e 'ssh ... -J gpu40901' --exclude '__pycache__' \
  rented4090:.../public_scenes/requests/2026-09-10_lite3_camera_ablation/ \
  public_scenes/requests/2026-09-10_lite3_camera_ablation/
shasum -a 256 -c public_scenes/requests/2026-09-10_lite3_camera_ablation/manifest.sha256
```

- Manifest: **2,524 files** (round 1: 787; round 2: 1,091; round 3: 1,571;
  round 4: 2,211), covering all thirty-five `cam_*` run directories, all
  thirty-five supervisor records, and the whole request directory; 281 of the
  lines are `cam_c7_*`. Remote self-verification: 0 non-OK lines.
- **Local verification: 2,524 of 2,524 lines OK, 0 FAILED, exit 0.**
- Transferred back: 261 files / 195,090,111 bytes of run evidence, 20 files /
  745,158 bytes of supervisor records, 14 files / 707,503 bytes of request
  files. No `--delete` in either direction; no local file was removed.

Returned local paths (all under `EXP`), new in round 5:

- `public_scenes/runs/cam_c7_fused_level_v{1..5}/`
- `runs/cam_c7_fused_level_v{1..5}/`
- `public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight/`:
  `c7_fused_level.json`, `c8_fused_level_720.json`, both `_stdout.txt`, the
  fourteen round-5 PNGs (`c7_*` and `c8_*` `_start_fused_rgb`,
  `_start_ideal_rgb`, `_start_head_rgb`, `_start_d435_rgb`,
  `_start_d435_depth_mm`, `_start_depth_mm`, `_start_coverage`),
  `resources_before_round5.txt`, `link_launch_dir_round5.txt`,
  `run_preflight_round5_stdout.txt`
- `public_scenes/requests/2026-09-10_lite3_camera_ablation/`:
  `matrix_driver_round5_stdout.txt`, `summarise_round5_stdout.txt`,
  `ffprobe_round5_stdout.txt`, updated `matrix_log.jsonl` (35 lines),
  `matrix_log.jsonl.txt`, `matrix_stdout.txt`, `condition_summary.json`,
  `condition_summary.md`, `ffprobe_frame_counts.json`, `manifest.sha256`, and
  this `OPUS_RETURN.md`

`OPUS_RETURN.md` was written after the manifest, is deliberately excluded from
it, and was copied to the remote afterwards. Round-1 to round-4 files were
preserved on both sides, including `preflight/round1_failed_ratio_criterion/`
and `preflight/round2_c1_stage6_blocked/`.

## R5.7 Deviations from the round-5 package steps

- **R5-D1 — Unattended preflight driver.** The executor's per-command ssh
  timeout is shorter than the preflight, so the lead's own
  `REQ/preflight/run_preflight_round5.sh` was started with `setsid nohup ... &`
  and polled, instead of being run in the foreground. The script itself was
  executed unchanged and hash-verified before use.
- **R5-D2 — ffprobe path and script reuse.** Unchanged from round-1 D3 /
  R2-D4 / R3-D2 / R4-D2: bare `ffprobe` is not on the remote default PATH, so
  `official_r2r/official_env_024/bin` was prepended. The package's step-5
  ffprobe block was not retyped; the byte-identical round-3 copy
  `REQ/ffprobe_round3.py` was executed unchanged (it globs all `cam_*` runs, so
  it covers round 5), and its stdout is at `REQ/ffprobe_round5_stdout.txt`.
- **R5-D3 — Summariser output redirected.** For the same timeout reason the
  summariser's output was captured to `REQ/summarise_round5_stdout.txt` instead
  of the terminal. The command and its default `--out` / `--md` targets are the
  package's, unchanged.
- **R5-D4 — `__pycache__` excluded from the manifest as well as from rsync.**
  New in round 5 and the only deviation that changes a package command. The
  fused plugin is imported from `REQ/`, so the official env wrote
  `REQ/__pycache__/fused_camera.cpython-39.pyc` and
  `fused_camera_plugin.cpython-39.pyc` on the remote — two derived artefacts of
  lead-authored `.py` files that did not exist in rounds 1-4. The manifest was
  first generated with the package's exact `find` (2,526 lines, including those
  two `.pyc`), then regenerated with `! -path '*/__pycache__/*'` (2,524 lines)
  so that the manifest lists exactly what the established `__pycache__`-free
  rsync returns and stays verifiable locally. Without this the two `.pyc` lines
  would have read FAILED on the local check purely because bytecode is not
  returned. No `.py` file, and no other manifest entry, was affected; the local
  request directory contains no returned `.pyc`.
- **R5-D5 — Both conditions handed to the driver; C8 stopped by the gate.**
  The package's step 4 command lists both conditions, so both were passed.
  `run_matrix.sh` refused C8 on its preflight verdict and logged
  `SKIP condition c8_fused_level_720: preflight report did not pass all stages`
  before any C8 process started. The executor did not separately suppress C8,
  and did not launch, rerun or delete anything for it.
- **R5-D6 — Jump-host routing.** Every ssh and rsync used
  `-o BatchMode=yes -o ConnectTimeout=25 -J gpu40901` per the package's round-5
  connectivity note. The direct `ssh rented4090` alias was never exercised.

No other deviation. `conditions.json`, the ten condition YAMLs, both eval
configs, `fused_camera.py`, `fused_camera_plugin.py`, `preflight_fused.py`,
`run_cam_eval.sh`, `run_matrix.sh`, `matrix_driver_round5.sh`,
`run_preflight_round5.sh` and the summariser were executed exactly as authored
and hash-verified on the remote before use. No lead-authored file was edited.
No geometry, sign, criterion, fusion parameter or evaluator logic was touched.

## R5.8 Remaining issues and what the lead must decide

1. **C8 is blocked by a throughput bound, not by a correctness one, and five
   authorized runs are unused.** Stage 8 measured 226.47 ms/frame against
   `conditions.json` `preflight.fused.max_fusion_ms_per_frame` 200.0 — over by
   13 percent — while C8's stage 6 passed with the *better* coverage of the two
   conditions (1.23 percent uncovered against C7's 6.01 percent) and an
   equivalent head-region error (1.615 against 1.612). C7 itself passed with
   135.70 ms, so the bound separates the pair rather narrowly at the 640x480 /
   1280x720 D435i split. Whether to raise the bound, speed up the
   reprojection, or accept C8 as untested is the lead's call; the executor
   changed nothing and did not retry. Evidence:
   `REQ/preflight/c8_fused_level_720.json` stage 8 traceback,
   `REQ/preflight/c8_fused_level_720_stdout.txt`, and the seven C8 PNGs.
   Note that the 200 ms bound was never a run-time blocker in practice: at
   135.70 ms and about 55-146 steps per episode, fusion added roughly 8-20 s to
   a C7 episode, and all five C7 runs finished in 272-333 s against the 1,800 s
   deadline.
2. **C7 scores 0/10 and its episode 1 never reached the goal radius.** This is
   the only zero-oracle-success episode in the whole matrix, from a condition
   whose virtual geometry is identical to C5 (2/10). The executor reports the
   numbers and the C5-versus-C7 contrast in R5.5 without attributing the
   difference to the fusion's uncovered corners, its reprojection error, or
   System 1 or System 2; that diagnosis, and whether a 6 percent black
   bottom-corner region is an acceptable deployment image, is the lead's.
3. **The fused image is verified correct, so the 0/10 is not a plumbing
   failure.** `fused_equals_offline_recompute` is true, the head region matches
   the ideal render at 35.2 dB PSNR, every sensor sits at its configured pose,
   and all five runs exited 0 with a learned STOP in all ten episodes. Any
   explanation of the result therefore has to be about what the model does with
   a correctly fused image, not about whether the image reached the model.
4. **The round-3 frame-count anomaly is unchanged.**
   `cam_c1_lite3_rig_v1` episode 2 still has 502 `vis_debug` frames against
   501 steps, the only mismatch among 70 videos. It was neither touched nor
   rerun; the criterion question from R3.8 item 1 is still the lead's.
5. **Run budget.** 35 of the 40 authorized runs are consumed (30 in rounds 1-4,
   5 in round 5). The 5 unused runs are the C8 allocation and remain
   authorized for C8 only; anything else needs new authorization from Dr Sun.
6. **The head geometry is still partly estimated.** The head camera's pitch and
   intrinsics were measured on the robot on 2026-09-11, but its height and
   forward offset and the whole D435i pose are mesh/URDF estimates, as
   `conditions.json` `geometry_status` records. Any deployment conclusion from
   C7 inherits that status.
7. The round-2 observation about `public_eval_v1`'s differing evaluator hash
   inside the frozen baseline evidence is unchanged and was again left alone.
8. Commit status: **nothing staged, nothing committed.** No git command was run
   in the local repository. The Trellis task remains at `review`.

## Round 5b (2026-09-11) — written by the lead

The round-5b executor subagent synced REQ/ (26 authored files OK), recorded resources, ran the c8 preflight and started the
matrix driver, then stopped itself while waiting on its own watcher (no report). The lead monitored the remote driver and
performed steps 5-7. Connectivity: `ssh -J gpu40901 rented4090` throughout.

Preflight c8_fused_level_720 (`preflight/c8_fused_level_720.json`, written 2026-09-11T07:26:23Z): ALL_STAGES_PASSED, nine stages.
Coverage head 0.7726 / d435 0.2002 / blend 0.0149 / none 0.0123; error vs ideal head 1.615 / d435 1.063 / blend 1.103 mean abs
levels; fused_equals_offline_recompute true; fraction differing from ideal 0.7029; fusion 244.2 ms mean, 250.1 ms max (bound 300);
sensor states head 0.40 m / 0.27 m / pitch_down -16.7, d435 0.42 m / 0.25 m / +20.0, rgb and depth 0.40 m / 0.27 m / 0.

Matrix (`matrix_driver_round5b_stdout.txt`): START 07:28:31Z, MATRIX_DRIVER_DONE rc=0 at 08:08:46Z.

| Run | Exit | Timed out | Wall s | Ep1 S/O/NE m/steps | Ep2 S/O/NE m/steps |
| --- | --- | --- | --- | --- | --- |
| cam_c8_fused_level_720_v1 | 0 | no | 340.7 | 1/1/1.97/72 | 0/1/7.46/95 |
| cam_c8_fused_level_720_v2 | 0 | no | 350.2 | 1/1/2.81/66 | 0/1/8.49/117 |
| cam_c8_fused_level_720_v3 | 0 | no | 536.3 | 0/1/17.27/173 | 0/1/8.86/106 |
| cam_c8_fused_level_720_v4 | 0 | no | 571.8 | 0/1/17.33/167 | 0/1/8.71/125 |
| cam_c8_fused_level_720_v5 | 0 | no | 557.7 | 0/1/17.54/170 | 0/1/9.68/111 |

Learned STOP 10/10; ep1 collisions 0 in all runs; ep2 collisions 4-11. Total c8: 2/10.

Steps 5-7: `summarise_conditions.py` re-run on the remote from the EXP root with the official env python
(`summarise_round5b_stdout.txt`; table regenerated for 40 runs plus B0). `ffprobe` is not installed on the remote (no
`ffprobe` binary under $HOME or /opt), so `ffprobe_round3.py` was run on the lead's Mac from the local EXP root after the return
(`ffprobe_round5b_stdout.txt`: 160 videos probed, 0 errors; all ten c8 vis_debug frame counts equal `steps`); the resulting
`ffprobe_frame_counts.json` was uploaded before the final manifest. Manifest regenerated on the remote with the round-5 find
(cam_* run and supervisor directories plus REQ/, excluding manifest.sha256, OPUS_RETURN.md and __pycache__); remote self-check OK;
local `shasum -a 256 -c` result recorded in `review/LEAD_REVIEW.md` round-5b addendum. Returned: `public_scenes/runs/cam_c8_*`
(5 dirs), `runs/cam_c8_*` (5 dirs), REQ/ except lead-owned files. No commit.

## Round 6 (2026-09-11): C9, fused virtual camera 9 degrees down

Written by the lead, who drove this round directly: the round-5b executor subagent stopped itself twice while idling on its
own watcher, so round 6 was run over `ssh -J gpu40901 rented4090` from the lead session with every step recorded here.

- Sync gate in: 14 files uploaded (round-6 code, conditions, drivers, package, provenance, c9 YAML).
  `authored_files.sha256` verified 27/27 OK on the remote from `work/InternNav` before launch.
- Preflight 12:37 UTC: `ALL_STAGES_PASSED`, nine stages. Uncovered 3.30 pct, head 63.6 pct, head-region PSNR 34.66 dB,
  d435-region 39.73 dB, fusion 256.4 ms mean, implied floor gap 0.1576 m, all sensor poses exact
  (virtual and evaluator depth 9.0 deg down, head 16.7 deg up, D435i 20.0 deg down), fused rgb bit-identical to the
  offline recompute and differing from the ideal render in 71.8 pct of pixels.
- Matrix 12:38-13:06 UTC: `cam_c9_fused_down9_v1..v5`, all exit 0, no timeouts, wall 366.6 / 301.2 / 331.8 / 328.8 / 332.3 s.
  `MATRIX_DONE`, `MATRIX_DRIVER_DONE rc=0`.
- Summary recomputed on the remote; ffprobe run locally (the remote has no ffprobe): 180 videos, no errors.
- Result: c9 1/10 (ep1 0/5, ep2 1/5), oracle 5/10. Analysis in `review/LEAD_REVIEW.md` round-6 addendum.
- Manifest: scope stated explicitly for the first time (see the review addendum); 3,190 lines, remote self-check 0 non-OK,
  local `shasum -a 256 -c` recorded in the review after the lead-owned files were uploaded.
