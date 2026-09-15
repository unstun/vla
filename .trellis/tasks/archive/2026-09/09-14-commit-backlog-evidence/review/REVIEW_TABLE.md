# Review table: backlog commit (task 09-14-commit-backlog-evidence)

Generated 2026-09-14 from `review/classification.json`. Full per-commit path lists: `review/group_NN.txt`.

- Committed in total: **4,201 paths, 360.8 MB** (before git compression).
- Local-only: **29,981 files, 3,792.5 MB** in 15 directories. Each has a scoped `.gitignore` block and a `LOCAL_ONLY_BYTES.sha256`; all 15 verify.
- Left untracked: 10 browser-tool files (`.playwright-cli/`, `output/playwright/`).

## Commits

| # | Message | Paths | MB | Already tracked, modified | Main directories |
|---|---|---:|---:|---:|---|
| 1 | `chore(trellis): update templates to 0.6.15` | 42 | 0.4 | 32 | `2026-09-09_trellis_0_6_15` (10); `.trellis/scripts/common` (5); `.agents/skills/trellis-meta` (4) |
| 2 | `chore: path-specific ignores and local-only manifests` | 16 | 4.1 | 1 | `.gitignore` (1); `2026-08-19_omnivla_edge_orin64` (1); `2026-08-19_omnivla_lite3_receive_only` (1) |
| 3 | `docs(omnivla): Aug 18-19 CUDA, edge, receive-only and audit records` | 312 | 2.4 | 0 | `2026-08-19_omnivla_vla_evidence_audit` (107); `2026-08-19_omnivla_original_cuda_gpu40901` (65); `2026-08-19_omnivla_edge_orin64` (42) |
| 4 | `docs(tic-vla): Aug 20 Orin reproduction and Active MVP v2 records` | 98 | 5.3 | 0 | `2026-08-20_tic_vla_orin_pretrained` (71); `2026-08-20_tic_vla_lite3_active_mvp_v2_no_motor` (17); `.trellis/tasks/08-20-tic-vla-orin-upstream-reproduction` (6) |
| 5 | `docs: Sep 8-11 TIC-VLA DynaNav, NaVILA and DualVLN trials, incl. camera-ablation runs` | 1620 | 237.6 | 1 | `2026-09-08_dualvln_rented4090` (997); `2026-09-08_tic_vla_dynanav_5070ti` (487); `2026-09-08_navila_8b_quantized_5070ti` (93) |
| 6 | `docs(lightnav): Sep 9 LightNav-0 5070 Ti and 4090 demo records` | 506 | 53.1 | 6 | `2026-09-09_lightnav0_official_demo_rented4090` (441); `2026-09-09_lightnav0_5070ti_inference` (57); `.trellis/tasks/09-09-lightnav0-5070ti-inference` (4) |
| 7 | `docs(navdp): Sep 10 X-NavDP Lite3 trial` | 166 | 7.0 | 0 | `2026-09-10_x_navdp_lite3_rented4090` (158); `.trellis/tasks/09-10-navdp-lite3-rented4090` (6); `references/upstream/2026-09-10_navdp_lite3` (2) |
| 8 | `docs(camera): Sep 10-11 camera-study tasks and Sep 10-11 surveys` | 238 | 5.8 | 0 | `2026-09-10_navigation_vla_reliability_sources` (140); `2026-09-10_lite3_cameras_web_sources` (46); `.trellis/tasks/09-10-internvla-n1-camera-ablation-sim` (34) |
| 9 | `feat(isaac): InternVLA-N1 Lite3 Isaac loop, Phases A-D` | 1176 | 44.6 | 6 | `2026-09-11_lite3_isaac_v12_vla` (1141); `references/upstream/2026-09-11_lite3_sim_bridge` (17); `.trellis/tasks/09-11-internvla-n1-lite3-isaac-sim` (9) |
| 10 | `docs: sync indexes, memory and journal` | 27 | 0.5 | 8 | `.trellis/tasks/09-14-commit-backlog-evidence` (19); `.trellis/workspace/sun` (2); `README.md` (1) |

## Worth a look before approving

1. **Commit 1 includes your `AGENTS.md` edit**, the single added line `Project override: use English by default.`
2. **Staged Phase A paths.** The 74 staged Phase A paths are unstaged first and committed in commit 9, unchanged.
3. **Committed files over 5 MB** (all text):
   - commit 5: `.pipeline/experiments/2026-09-08_tic_vla_dynanav_5070ti/demo/runs/20260908T144555Z_dd190e/telemetry.jsonl` (33.3 MB)
   - commit 5: `.pipeline/experiments/2026-09-08_tic_vla_dynanav_5070ti/demo/runs/20260908T153532Z_615007/telemetry.jsonl` (7.9 MB)
   - commit 5: `.pipeline/experiments/2026-09-08_tic_vla_dynanav_5070ti/demo/runs/20260908T151850Z_e8fd96/telemetry.jsonl` (7.7 MB)
   - commit 5: `.pipeline/experiments/2026-09-08_dualvln_rented4090/public_scenes/runs/cam_c1_lite3_rig_v1/trace_0/skokloster-castle_0002.jsonl` (6.5 MB)
4. **Figures the documents cite will not be in git.** 243 local-only images, videos and PDFs (765 MB) are named in tracked Markdown, most of them in DualVLN (103), LightNav (58) and Isaac (43). Someone reading from git alone sees the file name and hash, not the picture.
5. **Possible exceptions**, currently local-only under the text-only rule. Say if you want them tracked:
   - three episode definitions we wrote for the public Habitat scenes: `preview.json.gz`, `val_unseen.json.gz`, `zh_between_two_chairs.json.gz` (2.8 KB in total; the official R2R `.json.gz` stay local);
   - four TIC-VLA Orin waypoint arrays, `runs/013_offline_cuda/*_waypoints.npy` (1.6 KB in total).
6. **Deferred:** `output/playwright/` holds three TIC-VLA demo screenshots from 2026-09-08. They stay untracked and not ignored, per the plan.
7. **Commit 2 also carries earlier tasks' ignore rules.** Besides this task's block, commit 2 includes the uncommitted `.gitignore` blocks
   (lines 84-159) written during the TIC-VLA DynaNav, NaVILA, LightNav, X-NavDP and Isaac tasks: models, checkpoints, work copies, the Isaac bundle and Phase B/C run bytes.
8. **Commit 10** will also refresh the hot-zone status brief, recent changes and the journal. I show you those edits before that commit.

## Independent check (trellis-check, 2026-09-14)

- The 4,201 group paths equal untracked + modified + staged − deferred exactly: 0 duplicates, 0 missing, and none are ignored.
- The newly ignored files equal the 29,981 local-only files exactly, including with `core.ignorecase=false`.
- No committed path is binary; the only files over 5 MB are four `.jsonl`.
- Probes for `.pdf/.png/.mp4/.zip/.step` outside the scoped directories are not ignored.
- Two classifier bugs were fixed: a re-run in a fresh session would have lost the local-only list, and a staged rename could drop its old path. Output did not change.
- Five `.gitignore` comments were corrected; two had wrong provenance claims.

## Local-only directories

| Directory | Files | MB | Rules |
|---|---:|---:|---|
| `.pipeline/experiments/2026-09-08_dualvln_rented4090` | 4,561 | 2,551.1 | scene_data/, work/, *.bz2, *.gz, *.jpg, *.mp4, *.png, *.pyz |
| `.pipeline/experiments/2026-09-11_lite3_isaac_v12_vla` | 11,873 | 439.3 | *.jpg, *.mp4, *.npy, *.png |
| `.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090` | 8,338 | 266.7 | *.STL, *.f64, *.jpg, *.mp4, *.npy, *.npz, *.onnx, *.png, *.tgz, *.zip |
| `.pipeline/experiments/2026-09-08_tic_vla_dynanav_5070ti` | 218 | 262.8 | work/, work/, work/, *.aiff, *.gz, *.jpg, *.mp4, *.pdf, *.png, *.wav |
| `.pipeline/survey/2026-09-10_lite3_cameras_web_sources` | 8 | 75.2 | *.pdf, *.png |
| `.pipeline/experiments/2026-08-19_omnivla_original_cuda_gpu40901` | 4,267 | 74.7 | dlimp_openvla/, transformers-openvla-oft/, *.jpg |
| `.pipeline/experiments/2026-09-10_x_navdp_lite3_rented4090` | 526 | 71.7 | *.STL, *.jpg, *.mp4, *.npz, *.obj, *.onnx, *.png |
| `.pipeline/experiments/2026-08-20_tic_vla_orin_pretrained` | 13 | 18.0 | *.npy, *.whl |
| `.trellis/tasks/09-10-internvla-n1-camera-ablation-sim` | 53 | 17.1 | *.jpg, *.png |
| `.pipeline/experiments/2026-09-08_navila_8b_quantized_5070ti` | 30 | 8.7 | *.jpg |
| `.pipeline/experiments/2026-08-19_omnivla_edge_orin64` | 12 | 3.8 | *.gz, *.jpg, *.whl |
| `.pipeline/experiments/2026-08-19_omnivla_vla_evidence_audit` | 8 | 1.9 | *.jpg, *.png |
| `.pipeline/experiments/2026-09-09_lightnav0_5070ti_inference` | 65 | 0.7 | *.jpg, *.tgz |
| `.pipeline/experiments/2026-08-20_tic_vla_lite3_active_mvp_v2_no_motor` | 7 | 0.4 | *.jpg |
| `.pipeline/experiments/2026-08-19_omnivla_lite3_receive_only` | 2 | 0.3 | *.jpg |

## Modified tracked files per commit

- commit 1: `.agents/skills/trellis-before-dev/SKILL.md`, `.agents/skills/trellis-check/SKILL.md`, `.agents/skills/trellis-meta/SKILL.md`, `.agents/skills/trellis-meta/references/platform-files/agents.md`, `.agents/skills/trellis-meta/references/platform-files/hooks-and-settings.md`, `.agents/skills/trellis-meta/references/platform-files/platform-map.md`, `.claude/hooks/inject-subagent-context.py`, `.claude/skills/trellis-before-dev/SKILL.md`, `.claude/skills/trellis-check/SKILL.md`, `.claude/skills/trellis-meta/SKILL.md`, `.claude/skills/trellis-meta/references/platform-files/agents.md`, `.claude/skills/trellis-meta/references/platform-files/hooks-and-settings.md`, `.claude/skills/trellis-meta/references/platform-files/platform-map.md`, `.codex/agents/trellis-check.toml`, `.codex/hooks/inject-subagent-context.py`, `.cursor/hooks/inject-subagent-context.py`, `.cursor/skills/trellis-before-dev/SKILL.md`, `.cursor/skills/trellis-check/SKILL.md`, `.cursor/skills/trellis-meta/SKILL.md`, `.cursor/skills/trellis-meta/references/platform-files/agents.md`, `.cursor/skills/trellis-meta/references/platform-files/hooks-and-settings.md`, `.cursor/skills/trellis-meta/references/platform-files/platform-map.md`, `.trellis/.template-hashes.json`, `.trellis/.version`, `.trellis/scripts/common/active_task.py`, `.trellis/scripts/common/paths.py`, `.trellis/scripts/common/task_context.py`, `.trellis/scripts/common/task_store.py`, `.trellis/scripts/common/task_utils.py`, `.trellis/scripts/task.py`, `.trellis/workflow.md`, `AGENTS.md`
- commit 2: `.gitignore`
- commit 5: `.trellis/spec/backend/index.md`
- commit 6: `.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/OPUS_EXECUTION_PACKAGE.md`, `.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/README.md`, `.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/setup/preparation_manifest.json`, `.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/setup/preparation_validation.json`, `.trellis/tasks/09-09-lightnav0-official-demo-rented4090/prd.md`, `.trellis/tasks/09-09-lightnav0-official-demo-rented4090/task.json`
- commit 9: `.pipeline/experiments/2026-09-11_lite3_isaac_v12_vla/README.md`, `.pipeline/experiments/2026-09-11_lite3_isaac_v12_vla/scripts/collect_run.sh`, `.pipeline/experiments/2026-09-11_lite3_isaac_v12_vla/scripts/phase_a_run_docker.sh`, `.trellis/tasks/09-11-internvla-n1-lite3-isaac-sim/design.md`, `.trellis/tasks/09-11-internvla-n1-lite3-isaac-sim/implement.md`, `.trellis/tasks/09-11-internvla-n1-lite3-isaac-sim/prd.md`
- commit 10: `.pipeline/experiments/README.md`, `.pipeline/literature/index.md`, `.pipeline/terminology/terminology.md`, `.trellis/workspace/sun/index.md`, `.trellis/workspace/sun/journal-1.md`, `bigmemory/热区/未关闭决策.md`, `bigmemory/热区/状态简报.md`, `bigmemory/热区/近期改动.md`

## Outcome (2026-09-15)

Dr Sun approved the table and asked for two small exceptions to be tracked: the three authored public-scene episode
`.json.gz` files and the four TIC-VLA waypoint `.npy`. That moved 3 paths into commit 5 (1,623) and 4 into commit 4
(102). The local-only set is now 29,974 files.

| # | Commit | Paths |
|---|---|---:|
| 1 | `ab7c8414` | 42 |
| 2 | `b472a48c` | 16 |
| 3 | `540abf14` | 312 |
| 4 | `63002f85` | 102 |
| 5 | `0d134e49` | 1,623 |
| 6 | `0a816433` | 506 |
| 7 | `3cfa2189` | 166 |
| 8 | `7f743cfa` | 238 |
| 9 | `0374716f` | 1,176 |

Each commit's file list was checked equal to its group list at commit time. A later classifier re-run overwrote
`group_01.txt`–`group_09.txt`; they were rebuilt from these commits, and the script now leaves the lists of committed
groups alone.
