# Implementation plan

Order matters: local work and frozen thresholds first, remote CPU second, Isaac last. Each gate needs its check to
pass before the next step starts. Paths are relative to `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/`.

## A. Local, no remote access

- [x] A1 Re-check the facts this plan relies on: `planner_manager.cpp:171` text and hash, materializer SHA,
      `build_scan.py` refusals, `review_two_goal.py` cancel check (absolute 0.4 m), goal A distance along the route.
- [x] A2 Materialize `p2b_execution/builds/scan_04/src`; write and test `apply_scan_terminal_accel_fix.py`
      (refusal on wrong hash, refusal on wrong line text, exact one-line diff). Gate: tree diff against `scan_03/src`
      is one file, one line.
- [x] A3 `scan_fix_qualification/`: copy and extend the replay executable (boxes, follow-ups, endpoint, collision
      count, max acceleration); `make_fixtures.py`; `analyze_suite.py`; unit tests for fixture generation and
      analysis on synthetic logs.
- [x] A4 Write `scan_fix_qualification/thresholds.json` from PRD AC2-AC6 and record its SHA-256 in `PLAN.md` before
      any remote call.
- [x] A5 Launcher changes in `isaac_runner/run_two_goal_pilot.py` (SCAN hash gate, cancel option with its refusal
      rule, GPU peak and wall time) plus `capture_install_identity.py`. Tests: the gate refuses a mismatched
      workspace; the default request is byte-identical to the current one apart from the new recorded fields.
- [x] A5b `isaac_runner/make_walk_review.py` (design 5.1) plus a local prototype from `actual4` shown to Dr Sun;
      launcher hardlinking and the optional `--remote-only-bulk` return mode (design 5.2), with tests.
- [x] A6 Review: `trellis-check` on the changed code; a read-only independent review of the patch step and the suite.

Rollback point: all of A is local, new files plus launcher edits that are visible in `git diff`.

A2/A5 done 2026-09-17 (agent, verified by lead): `scan_04/src` differs from `scan_03/src` only at
`planner_manager.cpp:171` (`0c51df…` -> `6eec7d…`); the materializer reproduced `scan_03/src` byte-identically; 55 tests
pass. Notes: the install gate excludes `__pycache__`/`*.pyc` because `scan_03`'s recorded identity has none; the
file mixes CRLF and LF and the patch keeps line endings; GPU is sampled every 1 s via `nvidia-smi`.

## B. 5070 Ti host, CPU only (needs Dr Sun's Q1a approval)

- [x] B1 Sync gate: whitelist sync, hash check of the scan_04 source, the suite and the fixtures before running.
- [x] B2 `build_scan.py scan_04`; capture `install_identity.json`. Gate: build succeeds; install hashes recorded and
      returned.
- [x] B3 Native suite, both builds, new run ID `native_suite_<UTC>`. Gate: all returned hashes match locally.
- [x] B4 `analyze_suite.py` then AC1-AC6 verdicts. Stop here and report to Dr Sun if any criterion fails.

B done 2026-09-17: `scan_04` built (74 s), install identity captured (380 files), native suite
`native_suite_20260917T083723Z` VALID and passed AC0 and AC2-AC6. A6 done: suite review (analyzer integrity fix) and launcher review (render guard, post-run gate exit code,
cancel mismatch refusal, D9 text); go for C.

## C. 5070 Ti host, Isaac GPU (needs Dr Sun's Q1b approval and a pass in B)

- [x] C1 Check that no other GPU job is running; record GPU state before. Done 2026-09-17: 202 MiB, no compute
      apps, no containers, ports free; the series driver repeats this before every episode (`host_before`).
- [ ] C2 Episode 1 (trigger 0.40 m); return, verify hashes, run `review_two_goal.py`, render its walk review video.
      Record 41/41 and the SCAN hash gate result; stop rule per PRD D11. Done 2026-09-17:
      `two_goal_20260917T085059Z_scanfix_e01` passed 41/41, gates before/after passed (67 src, 380 install files),
      cancel stop x = -1.134 (inside the original build's failure band), GPU peak 7,136 MiB, host wall 129 s.
- [x] C3 Episodes 2-6 (0.40 m), then 7 (0.45 m) and 8 (0.50 m), one at a time with the same review. Stop rule:
      PRD D11; split: PRD D12. Driver: `scan_fix_qualification/run_isaac_series.py` (pauses on any non-pass for the
      lead to apply D11; ledger `scan_fix_qualification/isaac_series/series_ledger.jsonl`, episode 1 backfilled).
      Done 2026-09-17 08:58-09:20 UTC: 7/8 passed 41/41. Episode 3 failed 40/41 (goal-B raw stop dwell 0.88 s:
      one 0.1595 rad/s yaw-rate sample; RL policy on zero command without a PD stance hold, Dr Sun). Series
      continued per D11 (not repeated). Analysis: `scan_fix_qualification/isaac_series/e03_failure_analysis.md`.
      All SCAN hash gates and returned-hash checks passed; GPU peaks 7,086-7,262 MiB; about 182 s per episode.
- [x] C4 Record GPU state after; confirm the containers and ports are cleaned up. Done: ledger `host_after`
      202 MiB, no compute apps, no containers, ports free (09:20:37 UTC).
- [x] C5 Replay every new Isaac stop pose natively with both builds (CPU, seconds, same worker as B3). Done:
      `scan_fix_qualification/runs/native_replay_20260917T092127Z` (VALID, AC0 control reproduced, 79 returned files
      hash-verified). Original build rejects the resume plan at 6/8 new stops (e01-e06, gate values 1.513-1.563;
      e05 at x = -1.106 lies outside the sweep band but is rejected at its recorded y/yaw) and accepts e07/e08;
      candidate accepts 8/8 (max 0.590-0.600 m/s^2, endpoint <= 0.0355 m).

## D. Report and adoption

D1/D1b done 2026-09-17: `make_report.py --stop-replay-run runs/native_replay_20260917T092127Z` (figures,
`report_data.json`, video hardlinks), `make_report_page.py` (`report/index.html`, published privately as
https://claude.ai/artifact/VSTvZquqTiA4iGuwWabJ6v), `RESULT.md` (AC7 not met as written: 7/8).

- [x] D1 `scan_fix_qualification/make_report.py`: panels 1-10 of design.md section 5 from returned files only;
      PNG copies under `figures/` with manifest lines; HTML report published as a private Artifact.
- [x] D1b `scan_fix_qualification/RESULT.md`: native table, Isaac table (stop position, native verdict at that stop,
      arrival errors, wall time, GPU peak), claim boundary (PRD AC8).
- [x] D2 Dr Sun reviews. If he accepts: record `scan_04` as the accepted build in the HarnessVLN README, the parent
      task and the hot zone. If he rejects: record why; `scan_03` stays. Done 2026-09-17: adopted (PRD D14);
      recorded in `p2b_execution/README.md`, the parent PRD and the hot zone.
- [x] D3 Commit the text evidence (large bytes local-only with manifests); journal entry. Done 2026-09-17:
      `20f24308` (230 local-only lines added to `LOCAL_ONLY_BYTES.sha256`, all 468 verified and ignored), spec
      lessons in `.trellis/spec/backend/simulator-inference-evidence.md`.

## Validation commands

`review_two_goal.py` takes `RUN --output PATH`; `--output` is required (`review_two_goal.py:176-177`).

```bash
python3 -m pytest .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_fix_qualification -q
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_fix_qualification/analyze_suite.py
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution/review_two_goal.py <run dir> --output <run dir>/review.json
```
