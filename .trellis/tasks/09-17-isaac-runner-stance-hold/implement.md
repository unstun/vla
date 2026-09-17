# Implement: Isaac runner stance hold

Paths are relative to `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/` unless absolute.

## A. Local code (no remote calls)

- [x] A1 `isaac_runner/stance_hold.py` per design.md section 2, plus `isaac_runner/test_stance_hold.py` covering
      every AC1 case. Use synthetic sequences, including a torque-continuity check at entry and a rejoin blend
      check at 0, 0.125 and 0.25 s.
- [x] A2 `isaac_runner/materialize_runner_patch.py`:
      - insert the module source verbatim;
      - add CLI flags (`--stance-hold {off,auto}`, default `off`), setup, the per-step call, the applied-action
        feedback, gain writes with read-back, and the record and summary fields (design.md section 3);
      - regenerate `runner_external_episode.patch` and `source_hashes.json`;
      - extend `test_materialize_runner_patch.py`, including:
        - an `off`-path equivalence test on the materialized text;
        - a mock-env step test (fake robot with actuator tensors) for both modes;
        - a test that `off` never writes gains.
- [x] A3 `isaac_runner/qualify_stand_runner.py` and `isaac_runner/run_two_goal_pilot.py`:
      - pass `--stance-hold` into the runner argv;
      - record it in `run_request.json`;
      - refuse `--execute` when the flag mismatches the prepared package;
      - add tests.
- [x] A4 `isaac_runner/make_walk_review.py`: a mode label in the banner and mode shading on the timeline when
      `stance_mode` exists; unchanged output for old runs (test with a synthetic metrics file).
- [x] A5 `isaac_runner/analyze_stance_hold.py`: AC3 and AC5 metrics from a returned run (thresholds from a frozen
      `stance_hold_thresholds.json`, whose SHA-256 is recorded in this file before any run), plus tests.
      Frozen 2026-09-17 before any Isaac run: `isaac_runner/stance_hold_thresholds.json` SHA-256
      `fb8f9204c18e0b400ae2b7a2abc22bb052526538ff9713689759f15bff897c66`.
- [x] A6 A check pass (trellis-check) over A1-A5. All isaac_runner, p2b and scan_fix_qualification tests pass.

Validation:

```bash
python3 -m unittest discover -s .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner -p 'test_*.py'
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/materialize_runner_patch.py --check
python3 -m pytest -q .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_fix_qualification --ignore=.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_fix_qualification/runs --ignore=.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_fix_qualification/report --ignore=.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_fix_qualification/fixtures
```

Review gate: stop after A6 and ask Dr Sun to approve the C budget. Done 2026-09-17: A1-A5 implemented (isaac_runner
126 tests, materializer --check clean, patched runner `3e1bacf2…`); A6 check GO (analyzer fixed to fail AC3 on an
early-ended or hold-failed run). Open risk before C2: Kp steps immediately while position targets are delayed 0-4
substeps, so the entry torque can jump for up to 20 ms. Dr Sun approved the budget (PRD D3).

## C. 5070 Ti host (needs Dr Sun's approval)

- [x] C1 Stand A/B: `qualify_stand_runner.py`, `stand_probe` 60 s, first `--stance-hold off`, then `auto`; host idle
      check before each run; `analyze_stance_hold.py` gives the AC3 verdict. If AC3 fails, stop and report; C2 does
      not run.
      Done 2026-09-17 12:52-12:58 UTC on gpu5070ti: `isaac_runner/runs/stand_20260917T125239Z_hold_{off,auto}`
      (finish request at 57 s, both EXTERNAL_EPISODE_FINISHED, 25/25 returned hashes). AC3 **pass**
      (`stance_hold_qualification/stand_ab_20260917T125239Z.json`). FIXED_STAND 55.6 s: yaw ≤ 0.0038 rad/s,
      drift 2.5 mm, speed ≤ 0.013 m/s, min foot force 23 N, pitch ≤ 2.8°, entry at 0.40 s. Hold-off baseline over the
      same window: yaw 0.143, drift 3.4 cm, min foot force 0 N, pitch 6.6°. AC5 pass (no clip, no non-foot
      contact). **Finding, not covered by AC3/AC5:** at entry the body hopped for one step (vertical speed
      +0.21 m/s, |yaw rate| 0.30 rad/s, front feet unloaded to 2-4 N, settled in about 0.3 s). This matches the
      predicted delay mismatch (position targets 3 substeps late, Kp jump immediate; estimated torque ratio
      0.16 → 0.49). C2 paused for Dr Sun: fix the entry first or run as is.
- [x] C1a Entry fix (PRD D4, Dr Sun): 0.5 s smoothstep gain ramp at the start of STAND_TRANSITION, torque-
      preserving target; worst delay mismatch 7.3 % per step (was 200 %). AC7 added to the analyzer; thresholds
      re-frozen before the rerun: SHA-256 `12373448a8aee02534b529c69189bc5155bbe13cb0d17b632d260b075e075da5`
      (old file kept in `stance_hold_thresholds_history/`). Lead decision: AC7 window end tolerance 1 ms (float32
      sim times). AC7 on the C1 run fails as expected (yaw 0.302, vertical 0.210). Patched runner `1d33b43b…`;
      isaac_runner 142 tests.
- [ ] C1b Rerun the hold-on stand (60 s); hold-off baseline reused from C1.
- [ ] C2 Two-goal series with `scan_04` and `--stance-hold auto`: 8 episodes (6 cancel at 0.40 m, 1 at 0.45 m, 1 at
      0.50 m), reviewed like the SCAN series (41 checks, D11-style stop rule), with walk videos.
- [ ] C3 Host state after; containers and ports clean.

## D. Report

- [ ] D1 `RESULT.md` (AC3-AC6), figures (the stand A/B yaw and drift traces, the per-episode mode timelines) and
      a private Artifact page.
- [ ] D2 Dr Sun decides whether `--stance-hold auto` becomes the default for later pilots.
- [ ] D3 Commit (local-only bytes in the manifest), journal, hot zone, archive.
