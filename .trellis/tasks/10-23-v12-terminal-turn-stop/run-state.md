# Run state

## 2026-10-23 — package created (Claude Code session)

- Task created from Dr Sun's hypothesis; evidence checked read-only and written to `research/evidence.md`.
- No SSH, no remote build, no new physics. No code changed. Gates G1/G2/G3 not yet asked.
- Next: Step 0 in `implement.md`, then ask Dr Sun for G1 (read-only ultra9 audit).

## 2026-10-23T01:15:21-07:00 — Step 0 complete; awaiting G1 (Codex)

- Branch verified: `local/research-unpublished`; starting HEAD `b0918338f929fb89b443b8820553a9ef7fa33179`; no upstream.
- Read `AGENTS.md`, the full `.trellis/workflow.md`, `prd.md`, `research/evidence.md`, `implement.md`, and all 10 files in `implement.jsonl` (nine backend specs plus evidence). Also read the backend/guides indexes and `trellis-start` skill.
- Read all Step 0 parent materials: v291 `RESULTS.md`; paired24 `REPORT.md` and `PLAN.md`; v290 stop-timeline `REPORT.md`; v290 task `CLOSEOUT.md`. Read paired24 `analysis/DEFINITIONS.md` and the old read-only extractor to scope G1.
- Executed the requested `python3 ./.trellis/scripts/task.py start 10-23-v12-terminal-turn-stop`; status changed planning -> in_progress and session pointer was persisted. Context validation passed (10 implementation / 6 check entries); `task.py current --source` confirms this task.
- **Evidence correction:** saved `env.yaml:2100` sets `dynamic_resample_commands: true`. The fixed <=0.2 m/s zeroing is inside the inactive non-dynamic branch. Verified sampler/config/helper hashes and corrected evidence section 3 plus the PRD background/B6 factual premise. The low-speed stall remains observed; a fixed training floor does not follow. User notified. No command thresholds changed.
- **Budget issue for G2:** B2 contains 13 linear + 12 pure-yaw + 4 stop + 2 rotate/approach cells = 31 cells, requiring 93 fresh starts for three repeats; optional B4 adds 12. The suggested 40-run cap cannot cover the required matrix. Leave the matrix and cap proposal unchanged until the explicit G2 budget decision.
- **Phase A definition issue:** the requested <=0.2 and >=0.2 summaries overlap at exactly 0.2. Before extraction, freeze separate zero / (0,0.2) / exact-0.2 / >0.2 bins, then report both requested inclusive shares with the overlap disclosed. Define pure-yaw intervals, timestamp weighting, missing terminal windows and censoring before new metrics.
- Spec housekeeping noticed: generic backend index/quality scope still says no backend was imported, and the v291 plugin section still says physics untested; the dated v291 paired24 report supersedes that historical status. These stale summaries were not expanded into unrelated spec edits.
- Initial tracked tree was clean. Existing untracked paths were observed and left untouched: `hosts/2026-10-19_gpu5070ti_wifi_recovery/` and `versions/v221/` under E, four `.playwright-cli/` files, and four `output/playwright/` gallery files. Compact context omitted these, so full Git status is the dirty-state reference.
- G1 approval request scope, **pending**: ultra9, Phase A read-only audit of 34 retained attempts (10 v290 + 24 paired), one extraction campaign under `nice -n 19`, estimate 20–40 min; 0 new physics. For later Phase C, after B is reported and its measurements used: one native build/component-check campaign (14-package verification), two recorded controller replays (D07/CD12), one 32-heading geometry-probe campaign, and one strict53 cohort (53 offline cases), estimated 1–2 h; 0 new physics. Preserve failed receipts and scored outputs; no score-replacement run. No Phase C work before B.
- G2 and G3 remain pending and have not been asked. No SSH, remote build, physics, hardware, subagent, commit or push occurred. Step 0 records stay for the Phase A commit; no A/B/C/D phase is claimed passed.
- Next: ask G1 once with the above host/count/duration scope; wait for an explicit yes before SSH. After yes, freeze Phase A source/definitions, audit the retained recordings and return compact summaries/plots with source hashes. Bulk stays on ultra9.

`E` = `.pipeline/experiments/2026-09-26_newton_stair_reproduction`.

- Step 0 verification: task/context validation passed; all 19 checkpoint read-file hashes matched; `git diff --check` passed. Reviewed all six task-owned changed/new files (each 2.5–11.0 kB; documentation/JSON only). No phase completion commit yet.

## 2026-10-23T01:18:12-07:00 — G1 approved; Phase A preparation

- Explicit user yes recorded in task.json for ultra9 and the previously stated scope. G2/G3 remain pending; Phase C remains after B.
- Change boundary: one new audit directory with frozen analysis source, definitions, unit tests, compact tables/plots/report and provenance; task checkpoint/evidence records only. No navigation, policy or simulator changes.
- Read-only remote commands will inspect host availability and recording structure, then run frozen Python through SSH stdin using the existing worker interpreter under nice 19. Raw captures stay untouched on ultra9; compact JSON comes back locally.

## 2026-10-23T01:25:27-07:00 — Phase A source and definitions frozen

- Host preflight passed: ultra9 resolves to ubun, existing worker Python 3.12.13, nice 19; 34 required run directories present. No source/raw writes remotely.
- `2026-10-23_v12_command_range/frozen.json` binds definitions, plan, 34-run request, stdlib extractor, launcher and tests before extraction. All 14 definition/provenance tests passed; source compiles locally. Historical source hashes are bound for all 34 runs.
- Next: one `extract01` read-only campaign. Full JSONL/receipts and any failures are retained; no physics launcher.

## 2026-10-23T01:34:35-07:00 — Phase A extraction and verification complete

- One read-only `extract01` campaign finished: 34/34 analyses, 133,924 telemetry rows; all 102 source files (2,042,543,585 bytes) matched historical hashes and stable-read checks. Zero missing/error rows. Actual remote extraction 12.34 s, total launch 18.86 s; no remote files written, no new physics.
- Twenty-eight goal-circle windows and six fallback windows; all six fallbacks were historical scanner failures. All nine original scanner failures remain in the cohort. Exact-0.2 exposure was zero; bands and all interval totals reconcile.
- Low-speed exposure is 86.20–99.87% of nonzero translation time in circle windows. Paired v291: 114.44/115.01 s (99.50%). CD12 r1 and S04 r1 average commanded 0.04548/0.04582 m/s in the lowest band but signed progress only -0.00038/+0.00018 m/s. This supports the low-speed stall diagnosis without setting a steady-state floor.
- Thirty-nine pure-yaw intervals total 6.297 s. Longest 1.559 s; maximum heading change 50.4 degrees; no 90/180-degree evidence. All per-run bands and each interval/command/source row retained in the audit report/tables/JSON.
- Source remains frozen; 14 pre-freeze tests, source compilation and post-extraction identity/accounting checks passed. Three PNG/SVG scientific figures visually inspected: labels/units readable, all34 rows represented, short-interval limits disclosed. Plot guidance applied to the scientific file output; report follows the supplied research-report format and direct writing style.
- Dated training-branch correction retained; focused stance spec note added. No general workflow expansion. Phase B proposal records required93 runs on ultra9, <=120 simulated seconds/run including startup, estimated1–3h and4h wall cap; G2 has not been approved. C/D remain unstarted.
- Next: final file/size/diff check, local Phase A commit, then ask G2 once for the concrete proposal. No push.

## 2026-10-23T01:36:56-07:00 — Phase A final review; G2 request prepared

- Full task-owned file/size review: 41 files,1,473,716 bytes before the small quality receipt/final checkpoint; largest287,940 bytes. Only source, documentation, compact derived tables/receipts and scientific figures. No raw telemetry, weights, videos or full logs. Existing unrelated files remain excluded.
- Final checks passed: unchanged frozen source,14 unit tests, all34 run identities,102 source hashes, accounting, Python compilation, report links, plot provenance/visual review, context manifests and git diff whitespace. Detailed receipt: audit `results/quality_review.json`.
- Phase A is complete. This checkpoint is included in the local commit `research: audit V12 terminal command range across 34 recordings`. No push.
- Awaiting G2 explicit yes: ultra9,93 fresh flat-ground starts, optional assistance arm omitted,120 simulated seconds/run including startup, expected1–3h with4h total wall cap. Source/metrics freeze and zero-step loaded-module preflight precede scored physics. Proposal: `research/phase-b-proposal.md`. No B physics/C implementation/D evaluation has started; G3 remains pending.
