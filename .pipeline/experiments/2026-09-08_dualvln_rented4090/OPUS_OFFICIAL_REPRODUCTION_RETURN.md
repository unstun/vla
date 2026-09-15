---
origin: ai+remote_execution
reviewed: false
date: 2026-09-09
status: blocked_no_episodes_executed
executor: Opus
package: OPUS_OFFICIAL_REPRODUCTION_PACKAGE.md
supersedes_priority_of: OPUS_CORRECTION_PACKAGE.md
---

# Official Habitat R2R reproduction — execution return

## 1. Headline: the run did not happen

**Zero of the three episodes were executed. There are no official results, no
first-person videos and no top-down trajectory visualisation from this task.**

The package's acceptance condition — "execution of this fixed subset through the
official evaluator, verifiable results including failures" — is **not met**. What
follows is the blocker report the package asks for in that case, plus the
preparation that could be completed independently.

| Requested deliverable | Status |
| --- | --- |
| Three R2R `val_unseen` episodes through the official evaluator | **NOT EXECUTED** |
| Per-episode success / NE / OS / SPL | **NONE — no episode ran** |
| First-person videos | **NONE from this task** |
| Top-down trajectory visualisation | **NONE from this task** |
| Exact blocker reported | Done, three blockers, evidenced |
| Independent preparation | Done — see §5 |

No custom scene, no substitute dataset, no invented instruction and no
ground-truth action was used as a stand-in. The previous custom-scene runs are
untouched and are **not** re-presented as official results.

## 2. The three blockers, in the order they stop the run

### Blocker 1 (hard, needs Dr Sun) — Matterport3D scene mesh

`scripts/eval/configs/vln_r2r.yaml` sets `habitat.dataset.scenes_dir=data/scene_data/mp3d_ce`,
and `habitat.Env()` loads each episode's `scene_id` from it. Without the mesh the
official evaluator cannot construct an environment, so no episode can run.

Searched and **not present** on either machine: the local repository, all sibling
project directories under `/Users/sun/tongbu/study/phdproject/`, and the whole of
`/home/ubuntu` on the rented host. No MP3D, no `scene_data`, no `.glb`.

MP3D is not publicly downloadable. Verbatim from the Matterport3D project
repository:

> "To download the dataset, you must indicate that you agree to the terms of use
> by signing the Terms of Use agreement form, using your institutional email
> addresses, and sending it to: matterport3d@googlegroups.com"

- Terms of Use: `http://kaldir.vc.cit.tum.de/matterport/MP_TOS.pdf`
- After approval, the Matterport team grants access to `download_mp.py`.
  habitat-sim's `DATASETS.md` documents the Habitat-format download as
  `python download_mp.py --task habitat -o path/to/download/` (Python 2.7).

**This requires a signed agreement from an institutional email and an approval
email exchange. I cannot complete it, and no credential for it exists on either
machine.**

**Only one scene is needed**, not the 90-scene collection: **`2azQ1b91cZZ`**, placed at

```
official_r2r/data/scene_data/mp3d_ce/mp3d/2azQ1b91cZZ/2azQ1b91cZZ.glb
official_r2r/data/scene_data/mp3d_ce/mp3d/2azQ1b91cZZ/2azQ1b91cZZ.navmesh
```

I could **not** verify from an authoritative page whether `download_mp.py` exposes
a per-scene flag, because the script is only distributed after approval. If it
does, restricting to `2azQ1b91cZZ` avoids the ~15 GB full download.

### Blocker 2 (worked around, not resolved) — gated R2R-CE annotations

The InternRobotics distribution of the annotations is gated:

```
HTTP/2 401
x-error-code: GatedRepo
x-error-message: Access to dataset InternRobotics/InternData-N1 is restricted.
                 You must have access to it and be authenticated to access it. Please log in.
```

No HuggingFace token exists on either machine (checked `~/.cache/huggingface/token`,
`~/.huggingface/token`, and `HF_*` environment variables on both). Accepting the
gate is a user action.

**Worked around** by taking the annotations from their upstream origin instead:
the VLN-CE authors' own public `R2R_VLNCE_v1-3` release
(`https://drive.google.com/file/d/1T9SjqZWyR2PCLSXYkFckfDeIs6Un0Rjm/view`,
documented at `https://github.com/jacobkrantz/VLN-CE`; MP3D Terms of Use +
CC BY-NC-SA 3.0 US). Downloaded 2,608,469 bytes, SHA-256
`e2a81331524a6ca9a987d014a1affcb3b7174240cfae3647532bbaf68ef18404`.

**Caveat that must not be dropped:** this is the origin of R2R-CE, but it was
**not byte-compared** against InternRobotics' copy, because that copy is gated.
Any difference between the two is an unverified risk to strict parity.

### Blocker 3 (newly discovered here) — the pinned configs need habitat-lab v0.2.x

This one was not previously known, and it would have blocked the run even with
the MP3D data present. The pinned InternNav repository **pins no habitat-lab or
habitat-sim version anywhere** — `requirements/habitat_requirements.txt` lists
only model-side packages, and `setup.py`'s `[habitat]` extra reads that same
file. I therefore paired habitat-lab **v0.3.3** with the habitat-sim 0.3.3 already
verified in this experiment. That pairing is wrong, and two independent lines of
evidence show which version is right.

**Config-level evidence** — for each habitat-lab tag, whether
`habitat/config/habitat/simulator/agents/rgbd_agent.yaml` exists, and whether
`tilt_angle` / `action_space_config` are `SimulatorConfig` fields:

| tag | `agents/rgbd_agent.yaml` | `tilt_angle` + `action_space_config` | verdict |
| --- | --- | --- | --- |
| v0.2.3 | HTTP 200 | 2 of 2 | compatible |
| v0.2.4 | HTTP 200 | 2 of 2 | **compatible** |
| v0.2.5 | HTTP 200 | 1 of 2 | partial |
| v0.3.0 | HTTP 404 | 1 of 2 | incompatible |
| v0.3.1 | HTTP 404 | 1 of 2 | incompatible |
| v0.3.3 | HTTP 404 | 1 of 2 | incompatible — the version built here |

Observed on 0.3.3, in order as each was addressed:
1. `MissingConfigException: Could not find 'habitat/simulator/agents/rgbd_agent'`
   — the node exists but moved to group `habitat/simulator/sensor_setups`.
2. `ConfigKeyError: Key 'tilt_angle' not in 'SimulatorConfig'` — relocated onto
   the `look_up`/`look_down` action configs (same default, 15).
3. `ConfigKeyError: Key 'action_space_config' not in 'SimulatorConfig'` — removed
   after v0.2.4.

**Code-level evidence, independent of the config:**

```
ImportError: cannot import name 'try_cv2_import' from 'habitat.core.utils'
```

`internnav/habitat_extensions/vln/measures.py:9` imports `try_cv2_import`, and
the evaluator imports that module for Habitat registry side effects (upstream's
own comment says "do not remove"). `try_cv2_import` is defined in habitat-lab
v0.2.3, v0.2.4, v0.2.5 and v0.3.0, and **removed in v0.3.3**.

**Conclusion:** config evidence narrows to v0.2.3/v0.2.4; code evidence
independently excludes v0.3.3. The intersection is **habitat-lab v0.2.3 or
v0.2.4**, with v0.2.4 the strongest candidate.

**Status: DIAGNOSED, NOT VERIFIED END-TO-END.** No habitat-lab v0.2.4 environment
was built or run, so I am not claiming the run would succeed on it — only that
0.3.3 is demonstrably wrong and v0.2.4 is what the pinned files were written
against. Full detail in `official_r2r/setup/habitat_lab_version_diagnosis.json`.

I deliberately **stopped** hand-porting the config to 0.3.3. Two edits worked
(`rgbd_agent` group, `tilt_angle` relocation — both provably value-preserving),
but `action_space_config` selects the action-space implementation, and continuing
would have meant re-authoring upstream's evaluation config against a different
Habitat API. That is exactly what the package forbids. The derived YAML was
reverted to faithful: **2 lines differ from upstream, both asset paths.**

## 3. The three frozen episodes

Frozen **before** any model trial, by a rule that cannot depend on model outcomes:
group `val_unseen` by `scene_id`; keep scenes with ≥3 episodes; sort those
`scene_id`s lexicographically and take the first; within it sort by
`int(episode_id)` ascending and take the first three.

- Source: 1,839 episodes across 11 scenes; all 11 were eligible.
- Source SHA-256 `d173d8028537f30ab652dc5d24ead737e2b6010b6a4599f974351685710d18e8`.
- Selected scene `mp3d/2azQ1b91cZZ/2azQ1b91cZZ.glb` (252 episodes in scene).
- Derived subset SHA-256 `ea7ef5bc98904c5885d8a94abe83d6d932137a53a648ebdcbbbbe84e89e4735b`,
  47,374 bytes; episode objects copied through unchanged; `instruction_vocab`
  metadata preserved.

| episode_id | trajectory_id | geodesic (m) | instruction (verbatim) | outcome |
| --- | --- | --- | --- | --- |
| 10 | 57 | 7.113 | "Walk into the living room and keep walking straight past the living room. Then walk into the entrance under the balcony. Wait in the entrance to the other room." | **NOT EXECUTED** |
| 11 | 57 | 7.113 | "Walk across the floor and wait the archway." | **NOT EXECUTED** |
| 12 | 57 | 7.113 | "Move forward to the doorway on the opposite side of the hall.  Stop in the archway." | **NOT EXECUTED** |

Shared start `[16.4891, 0.1271, 8.9708]`, start rotation `[-0.0, 0.0, 0.0, 1.0]`,
goal `[16.4652, 0.1271, 1.8579]` radius 3.0, reference path 5 points.

**Property worth flagging:** all three share `trajectory_id` 57. R2R gives each
trajectory three independent human instructions, and the fixed rule landed on one
such group. The subset therefore tests **instruction variation over one route**,
not three distinct routes. The rule was fixed in advance, so I left the selection
unchanged rather than re-picking after seeing this. If the lead wants three
distinct trajectories, that is a **rule change to be made deliberately and before
the run**, not a post-hoc swap.

## 4. Commands and exit codes

| Job | Exit | Wall | Note |
| --- | --- | --- | --- |
| `official_env_setup_v1` | 1 | 128.5 s | conda-forge download timeout; also my needless `cmake` pin |
| `official_env_setup_v2` | 139 | 0.2 s | micromamba 2.1.1 segfault — `list --explicit` omits the `@EXPLICIT` marker |
| `official_env_setup_v3` | -15 | 366.4 s | deliberately SIGTERM'd to swap in the pre-staged habitat-lab |
| `official_env_setup_v4` | **0** | 247.6 s | `OFFICIAL_ENV_SETUP_COMPLETE` |
| `official_preflight_v1` | 0 | 5.8 s | first blocker: evaluator import (`uvicorn`) |
| `official_preflight_v2`…`v6` | 0 | ~6 s each | dependency and config-compat iteration (§2, blocker 3) |
| `official_preflight_final` | **0** | 6.7 s | recorded state with the faithful config |

The preflight exits 0 because it is a diagnostic that records failures; the stage
results inside it are what matter.

The official command is **prepared but never executed**, because
`official_r2r/scripts/run_official_eval.sh` refuses to run without the scene and
exits 3 with `BLOCKED_MISSING_MP3D_SCENE`:

```sh
cd work/InternNav && python scripts/eval/eval.py \
  --config ../../official_r2r/configs/habitat_dual_system_subset3_cfg.py
```

The command was **attempted** and refused. `official_r2r/runs/` is empty — no run
directory was created, because the scene check runs before any output directory
is made. The refusal is recorded at
`official_r2r/blocked_attempts/official_subset3_attempt1_20260909T083718Z.txt`:

```
attempted_run_id=official_subset3_attempt1
utc=2026-09-09T08:37:18Z
result=BLOCKED_MISSING_MP3D_SCENE
missing_path=official_r2r/data/scene_data/mp3d_ce/mp3d/2azQ1b91cZZ/2azQ1b91cZZ.glb
note=No episode was executed. No results, videos or metrics exist for this attempt.
```

**No execution ID exists to record**, because no evaluation process ever started.

## 5. What was completed independently

1. **Frozen subset** with selection manifest, source and derived hashes, and full
   original episode objects (§3).
2. **Official evaluator environment** (`official_env_setup_v4`, exit 0). One
   Python 3.9 environment holding habitat and the model together, as the official
   evaluator requires — unlike the earlier two-process trial:
   `habitat-lab 0.3.3, habitat-sim 0.3.3, habitat_baselines 0.3.3, torch 2.6.0+cu124,
   transformers 4.51.0, diffusers 0.32.2, flash_attn 2.7.3`; 131 packages pinned in
   `official_r2r/setup/official_env_pip_freeze.txt`. **This environment is now known
   to be the wrong habitat-lab (§2 blocker 3) and must be rebuilt on v0.2.4.**
3. **Derived configs** changing only what the package permits:
   - `official_r2r/configs/vln_r2r_subset3.yaml` — **2 of 77 lines differ from
     upstream**, both asset paths. Camera geometry, `forward_step_size`,
     `turn_angle`, `tilt_angle`, measurements and `success_distance` untouched.
   - `official_r2r/configs/habitat_dual_system_subset3_cfg.py` — paths and
     observability only. Verified field-by-field that `mode`, `num_history`,
     `resize_w/h`, `max_new_tokens`, `max_steps_per_episode` (500), `epoch`,
     `port`, `dist_url`, `model_name`, `eval_type`, `env_type` are identical to
     upstream.
4. **Output-only video patch** for the failure-video gap the package flagged.
   Upstream calls `images_to_video` only when `metrics['success'] == 1.0`, so
   failures lose their first-person + top-down composite. Changed to
   `len(vis_frames) > 0` with the outcome in the filename, at both sites
   (`_run_eval_dual_system` and `_run_eval_system2`). Policy, environment
   stepping, metrics and control flow untouched. `vis_debug=True` separately
   writes a per-episode first-person MP4 for **every** episode.
5. **Preflight harness** (`official_r2r/scripts/preflight_official.py`) that drives
   the pinned upstream modules and records exactly where they stop.
6. **Archival gate from lead-review R6 CLOSED.** All 864 observation PNGs plus
   both MP4s from the previous custom-scene runs are now local and hash-verified:
   **866 of 866 files, 0 missing, 0 mismatched**
   (`setup/observation_archive_verification.json`). This belongs to the previous
   task, reported separately as the package asked.

## 6. Environment, patches and sync status

**Pristine source untouched** at `7a5c62400ac45b313d9b709c740b64191556a242`.
`diff -rq` against `work/InternNav` shows exactly **three** differing files:

| file | change | origin |
| --- | --- | --- |
| `internnav/agent/__init__.py` | lazy-import shim | pre-existing |
| `internnav/model/encoder/__init__.py` | lazy-import shim | previous task |
| `internnav/habitat_extensions/vln/habitat_vln_evaluator.py` | **output-only** video patch | this task |

No model math, architecture, precision, weights, policy, control flow or
environment behaviour was changed. Checkpoint and encoder are the same verified
BF16 artefacts as before — nothing was re-downloaded.

Every script and config was authored locally, pushed with `rsync`, and SHA-256
compared local-vs-remote before each run. Large public artefacts that the rented
host fetches at ~25 KiB/s (the cp39 FlashAttention wheel, the habitat-lab v0.3.3
tree, and `uvicorn`/`fastapi`/`msgpack-numpy` wheels) were fetched on the
workstation from their authoritative sources and pushed up; habitat-lab is
recorded at commit `094d6be2f9d057e4781a68ae792132895fd4d3d0` (tag v0.3.3).

**Nothing staged or committed.** Both owned paths remain untracked.

## 7. Measurement scopes

No model was executed in this task, so there is **no latency, no VRAM and no
throughput to report**. The lead review's finding R1 (per-step CUDA peak resets,
end-to-end vs isolated S1/S2 timings) is therefore not addressed by new data
here; it stays open against the previous runs. When the official run does
happen, the evaluator must be instrumented to measure a **whole-run** CUDA peak
without per-step resets, and to label sampled `nvidia-smi` values with their
sampling interval and the fact that the device is shared with the Isaac Sim
container.

## 8. Local evidence paths

- `official_r2r/setup/data_requirements.json` — both data blockers, official
  access steps, exact scene and paths needed.
- `official_r2r/setup/habitat_lab_version_diagnosis.json` — blocker 3 with the
  full tag matrix and both evidence lines.
- `official_r2r/setup/episode_selection_manifest.json` — rule, hashes, and the
  complete original episode objects.
- `official_r2r/setup/frozen_episodes_summary.md` — human-readable subset.
- `official_r2r/setup/preflight_report.json` — per-stage results and tracebacks.
- `official_r2r/setup/official_env_pip_freeze.txt`, `habitat_lab_commit.txt`,
  `habitat_lab_tag.txt`.
- `official_r2r/configs/` — both derived configs.
- `official_r2r/scripts/` — `freeze_episodes.py`, `setup_official_env.sh`,
  `preflight_official.py`, `run_official_eval.sh`.
- `official_r2r/data/vln_ce/raw_data/r2r/val_unseen/val_unseen.json.gz` (source)
  and `.../r2r_subset3/val_unseen/val_unseen.json.gz` (frozen subset).
- `runs/official_env_setup_v*/`, `runs/official_preflight_*/` — raw logs, meta,
  process records.
- `official_r2r/blocked_attempts/` — the recorded, refused run attempt.
- `setup/observation_archive_verification.json` + `runs/sim_episode_v{1,2}/obs/`
  — the closed archival gate from the previous task.

## 9. Remaining blockers and next steps

1. **Dr Sun: sign the MP3D Terms of Use** (institutional email) and send it to
   `matterport3d@googlegroups.com`. On approval, fetch scene `2azQ1b91cZZ` only.
   This is the one step nobody else can take, and it gates everything.
2. **Optionally: accept the `InternRobotics/InternData-N1` gate** on HuggingFace
   and provide a token, so the annotations can be byte-compared against the
   VLN-CE original and blocker 2's caveat retired.
3. **Rebuild the evaluator environment on habitat-lab v0.2.4** with the matching
   habitat-sim, then re-run `preflight_official.py`. **This is independent of the
   MP3D request and can start immediately** — it would confirm or refute the §2
   diagnosis before the data arrives.
4. Only then run `official_r2r/scripts/run_official_eval.sh <run_id>` within the
   1,800 s GPU budget, and report official success / NE / OS / SPL per episode,
   with termination provenance separated from learned STOP.
5. Decide whether the frozen subset should stay as three instructions on one
   trajectory (§3) or be re-frozen on three distinct trajectories — deliberately,
   before any run.

Three episodes remain a bounded reproduction check, not reproduction of the
paper's aggregate success rate. **Infrastructure readiness is not reproduction,
and nothing in this return should be read as a navigation result.**

Task remains at `review` pending lead acceptance.
