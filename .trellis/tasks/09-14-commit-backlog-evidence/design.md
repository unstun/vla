# Design: committing the Aug 18 to Sep 14 backlog

## Classification

A single script, `classify_backlog.py`, lives in this task's directory. It is re-runnable and read-only on evidence.
It sorts every untracked or modified path into `track`, `local_only` or `deferred`. Rules, in order:

1. `deferred`: `.playwright-cli/**` and `output/**`.
2. `local_only`, by explicit directory (never a bare extension):
   - `**/vendor-src/transformers-openvla-oft/**` and any other vendored or work-copy tree named in an experiment's
     provenance (`work/`, `vendor-src/`, `venv/`, `.venv/`). OmniVLA receive-only `runtime/` is NOT one of these: it
     holds run logs, so its text is tracked.
   - `public_scenes/data/scene_data/**` (third-party Habitat scene assets, `.glb` and `.navmesh`).
3. `local_only`, by content type inside a named root: video, image, array, archive, CAD, audio, zip and PDF files.
   The `.gitignore` rule is scoped to that root, as in `/.pipeline/experiments/<root>/**/*.mp4`, which is
   path-specific.
4. `track`: everything else, including `.jsonl` of any size (decision D2).

The script prints per-root counts and bytes and writes the lists as JSON under `review/`. It changes no evidence.

## Manifests

- One file per root: `LOCAL_ONLY_BYTES.sha256`, in `shasum -a 256` format, sorted by path, with paths relative to the
  root. It lists every `local_only` file under that root, including files an older manifest already covers. That gives
  one uniform check per root without having to trust varied older formats.
- Older manifests are not edited.
- Sizes, storage location and the provenance pointer go into the `.gitignore` comment block for the root. Experiment
  READMEs are not edited (PRD R6).
- Roots: every experiment, task or survey directory where the classifier finds `local_only` files. On 2026-09-14 that
  meant 15: 13 experiments, `.trellis/tasks/09-10-internvla-n1-camera-ablation-sim` and
  `.pipeline/survey/2026-09-10_lite3_cameras_web_sources`.

## `.gitignore`

- One appended block per root, following the existing style (`.gitignore:85-159`): task, what is ignored, where the
  hash record is, how to regenerate or why the bytes cannot be regenerated.
- Existing blocks stay unchanged. The new blocks are appended as one section at the end of the file; where a root
  already had a block (TIC-VLA DynaNav, NaVILA, LightNav, X-NavDP, Isaac), the new comment says so.
- After writing, `git check-ignore --no-index` must return every `local_only` path and none of the `track` paths.

## Commit groups (oldest first)

| # | Message | Contents |
|---|---|---|
| 1 | `chore(trellis): update templates to 0.6.15` | Modified harness skills and hooks under `.agents/`, `.claude/`, `.codex/`, `.cursor/`; `.trellis/scripts/**`, `.template-hashes.json`, `.version`, `workflow.md`; `.pipeline/maintenance/2026-09-09_trellis_0_6_15/`; Dr Sun's `AGENTS.md` line (named separately in the table) |
| 2 | `chore: path-specific ignores and local-only manifests` | `.gitignore` and every `LOCAL_ONLY_BYTES.sha256` |
| 3 | `docs(omnivla): Aug 18-19 CUDA, edge, receive-only and audit records` | `2026-08-19_*` experiments, `deploy/omnivla_lite3_receive_only/`, tasks `08-18-omnivla-original-cuda-gpu40901` and `08-19-*`, the archived edge task, `.pipeline/external_tasks/`, the 2026-08-19 cold-zone record |
| 4 | `docs(tic-vla): Aug 20 Orin reproduction and Active MVP v2 records` | `2026-08-20_*` experiments, task `08-20-tic-vla-orin-upstream-reproduction`, `references/upstream/2026-08-20_tic_vla/` manifests, `2026-08-20_*` surveys |
| 5 | `docs: Sep 8-11 TIC-VLA DynaNav, NaVILA and DualVLN trials, incl. camera-ablation runs` | Those three experiments and the DualVLN preflight, their tasks and references, `2026-09-08_*` surveys, `.trellis/spec/backend/quantized-inference-evidence.md` and `simulator-inference-evidence.md` plus the spec index line |
| 6 | `docs(lightnav): Sep 9 LightNav-0 5070 Ti and 4090 demo records` | Both LightNav experiments (modified and untracked), their tasks, `REMOVED_MEDIA_20260914.tsv`, the `2026-09-09_*` survey |
| 7 | `docs(navdp): Sep 10 X-NavDP Lite3 trial` | Experiment, task, references |
| 8 | `docs(camera): Sep 10-11 camera-study tasks and Sep 10-11 surveys` | Tasks `09-10-lite3-camera-height-internvla-n1` and `09-10-internvla-n1-camera-ablation-sim`, `2026-09-10_*` and `2026-09-11_habitat_lab_024_sensor_api` surveys |
| 9 | `feat(isaac): InternVLA-N1 Lite3 Isaac loop, Phases A-D` | The 74 staged Phase A paths, all other Isaac experiment paths, task `09-11-internvla-n1-lite3-isaac-sim` edits, `2026-09-11_lite3_isaac_vla_integration` and `2026-09-14_body_clearance_margin*` surveys |
| 10 | `docs: sync indexes, memory and journal` | `.pipeline/experiments/README.md`, `literature/index.md`, `terminology.md`, the hot zone, the journal, this task |

- If one path fits two groups, the earliest date wins and the review table says so.
- A path left unclaimed by the grouping script stops the plan. It does not fall into a catch-all.
- Commit 2 goes first among the content commits, so every later `git add` of a root runs with its ignore rules already
  in place. That makes staging a local-only file impossible, not just unlikely.

## Staging mechanics

- `GIT_LITERAL_PATHSPECS=1 git add --pathspec-from-file=review/group_NN.txt`, never `git add -A` or `.`.
- Commit 2 also carries the uncommitted `.gitignore` blocks written by earlier tasks (lines 84-159: TIC-VLA DynaNav,
  NaVILA, LightNav, X-NavDP, Isaac). The review table names them.
- After each add, the staged list must equal the approved list: `git diff --cached --name-only` against the group
  file.
- `git commit` records the whole index, so the 74 already-staged Phase A paths must not sit in it during groups 1–8.
  Save their list (`git diff --cached --name-only > review/phase_a_staged.txt`), unstage them with
  `git restore --staged --pathspec-from-file=...`, and re-add them in group 9. This changes only the index. The
  files on disk stay byte-identical, which is checked by SHA-256 before and after.

## Risks

- A mistake in a large commit is permanent without a history rewrite, and there is no remote. Mitigations:
  - the review table is approved before anything is staged;
  - each commit is checked against its list;
  - the next commit waits until the check passes.
- Rollback before the next commit is `git reset --soft HEAD~1`. It changes history, so it is done only with
  Dr Sun's approval.
- The 291 MB of `.jsonl` inflates the repository; git's compression should cut that sharply. `git count-objects -vH`
  is reported after commit 10.
- Tracked Trellis task files for `in_progress` tasks will keep changing. That is normal; this task does not freeze them.
