# Implement: Isaac runner stance hold

Paths are relative to `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/` unless absolute.

## A. Local code (no remote calls)

- [ ] A1 `isaac_runner/stance_hold.py` per design.md section 2, plus `isaac_runner/test_stance_hold.py` covering
      every AC1 case. Use synthetic sequences, including a torque-continuity check at entry and a rejoin blend
      check at 0, 0.125 and 0.25 s.
- [ ] A2 `isaac_runner/materialize_runner_patch.py`:
      - insert the module source verbatim;
      - add CLI flags (`--stance-hold {off,auto}`, default `off`), setup, the per-step call, the applied-action
        feedback, gain writes with read-back, and the record and summary fields (design.md section 3);
      - regenerate `runner_external_episode.patch` and `source_hashes.json`;
      - extend `test_materialize_runner_patch.py`, including:
        - an `off`-path equivalence test on the materialized text;
        - a mock-env step test (fake robot with actuator tensors) for both modes;
        - a test that `off` never writes gains.
- [ ] A3 `isaac_runner/qualify_stand_runner.py` and `isaac_runner/run_two_goal_pilot.py`:
      - pass `--stance-hold` into the runner argv;
      - record it in `run_request.json`;
      - refuse `--execute` when the flag mismatches the prepared package;
      - add tests.
- [ ] A4 `isaac_runner/make_walk_review.py`: a mode label in the banner and mode shading on the timeline when
      `stance_mode` exists; unchanged output for old runs (test with a synthetic metrics file).
- [ ] A5 `isaac_runner/analyze_stance_hold.py`: AC3 and AC5 metrics from a returned run (thresholds from a frozen
      `stance_hold_thresholds.json`, whose SHA-256 is recorded in this file before any run), plus tests.
- [ ] A6 A check pass (trellis-check) over A1-A5. All isaac_runner, p2b and scan_fix_qualification tests pass.

Validation:

```bash
python3 -m unittest discover -s .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner -p 'test_*.py'
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/materialize_runner_patch.py --check
python3 -m pytest -q .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_fix_qualification --ignore=.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_fix_qualification/runs --ignore=.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_fix_qualification/report --ignore=.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_fix_qualification/fixtures
```

Review gate: stop after A6 and ask Dr Sun to approve the C budget.

## C. 5070 Ti host (needs Dr Sun's approval)

- [ ] C1 Stand A/B: `qualify_stand_runner.py`, `stand_probe` 60 s, first `--stance-hold off`, then `auto`; host idle
      check before each run; `analyze_stance_hold.py` gives the AC3 verdict. If AC3 fails, stop and report; C2 does
      not run.
- [ ] C2 Two-goal series with `scan_04` and `--stance-hold auto`: 8 episodes (6 cancel at 0.40 m, 1 at 0.45 m, 1 at
      0.50 m), reviewed like the SCAN series (41 checks, D11-style stop rule), with walk videos.
- [ ] C3 Host state after; containers and ports clean.

## D. Report

- [ ] D1 `RESULT.md` (AC3-AC6), figures (the stand A/B yaw and drift traces, the per-episode mode timelines) and
      a private Artifact page.
- [ ] D2 Dr Sun decides whether `--stance-hold auto` becomes the default for later pilots.
- [ ] D3 Commit (local-only bytes in the manifest), journal, hot zone, archive.
