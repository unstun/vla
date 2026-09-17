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

- [x] C1c Scripted walk (PRD D5), local build and check done 2026-09-17: `scripted_walk` case with a command script,
      side follow camera (heading fixed at the start yaw, 25 fps), entry-Kd variants `ramp` / `step1` /
      `step2p5`, and analyzer `walk` (AC8, D5 selection). Thresholds re-frozen before any walk run:
      `683a8ca6d9d26fe4c45af22fc449c1c05525fde9eb0fb3dc4125c4f2831b43b8`. Patched runner `120192be…`. Check GO;
      isaac_runner 188 tests.
- [x] C1d Four walk runs (off, ramp, step1, step2p5), then `analyze_stance_hold.py walk`, then a side-by-side video.
      Done 2026-09-17 14:56-15:03 UTC, `isaac_runner/runs/walk_20260917T145650Z_*`: all EXTERNAL_EPISODE_FINISHED, hashes
      match, no contact, reset or pose write. Report `stance_hold_qualification/walk_ab_20260917T145650Z.json`; video
      `stance_hold_qualification/walk_ab/walk_ab_side_view.mp4`. **No variant selected** (D5 rule): AC5 passes and
      AC8 a/c/d pass for all, but AC8 b / AC7 fails. Entry-window max |yaw rate| (landing, stop 1, stop 2):
      ramp 0.363 / 0.221 / 0.179; step1 0.280 / 0.063 / 0.117; step2p5 0.178 / 0.153 / 0.073 (limit 0.15).
      While held, the last 2 s of each stop show yaw ≤ 0.005 rad/s (hold off 0.065-0.117). Starts: max pitch in
      the 1 s after the command 2.7-3.7° (hold off 3.7-5.6°). Travel 2.98-2.99 m (hold off 3.12 m, -4 %).
      Stopped for Dr Sun.
- [x] C1e Survey before the next entry change (Dr Sun: look at recent papers and repositories first).
      `.pipeline/survey/2026-09-17_rl_pd_stance_hold_switch_survey.md` plus three notes in `research/rl_pd_switch_*`.
      Run-data check: the body was quiet before every entry (angular speed <= 0.17 rad/s), so a stricter body gate
      is withdrawn as the lead proposal. The next variant waits for Dr Sun's choice.
- [x] C1f Crossfade entry and landing grace (PRD D6, design.md section 8), local build only:
      - `stance_hold.py` gets the `xfade1s` / `xfade2s` variants and the grace, with unit tests:
        - entry step output (P(t), Kp0, Kd 1);
        - the mid-blend formula and its torque-sum identity;
        - exact end values at T_x;
        - FIXED_STAND at 2 s;
        - grace blocks arming before 1.0 s for the new variants only;
        - rejoin during the crossfade;
        - the old variants unchanged.
      - The materializer, launchers (`qualify_stand_runner.py`, and the `run_two_goal_pilot.py` passthrough),
        thresholds amendment plus re-freeze, then the check agent.
- [x] C1g Two walk runs (`xfade1s`, `xfade2s`), host idle check before each. Then:
      - `analyze_stance_hold.py walk` with the C1d hold-off baseline;
      - the pre-entry determinism comparison;
      - the side-by-side video (hold off, step1, xfade1s, xfade2s).
      Report to Dr Sun; C2 does not start before that.
      Done 2026-09-17 18:16-18:20 UTC, `isaac_runner/runs/walk_20260917T181650Z_hold_auto_{xfade1s,xfade2s}`:
      both EXTERNAL_EPISODE_FINISHED, 27/27 returned hashes, no contact, reset, pose write or torque clip.
      C1f: isaac_runner 202 tests, materializer --check clean, patched runner `0649747e…`, thresholds re-frozen
      `0be59927…` (descriptive amendment only; `683a8ca6…` archived). Implement and check agents both GO.
      **Both variants pass AC5, AC7 and AC8; the D5 rule selects `xfade1s`** (tie on the entry maximum 0.087,
      earlier `--on` argument wins). Report `stance_hold_qualification/walk_d6_20260917T181650Z.json`.
      Entry-window max |yaw rate| (limit 0.15): xfade1s 0.087 / 0.076 / 0.070; xfade2s 0.087 / 0.080 / 0.074.
      In both runs every entry-window maximum is the yaw rate already present on the entry row itself (the peak
      is one to a few steps later but no higher than 0.087), so the switch adds no visible kick. Over the whole
      2 s transition the numbers are the same, and max |vertical speed| is 0.013-0.022 (limit 0.05).
      Holds: tail yaw 0.0011-0.0017 rad/s and drift 0.12-0.31 mm at the two walking stops (hold off 0.065-0.117
      and 1.9-4.3 mm). Starts: max |pitch| 4.27 / 2.28 deg (hold off 5.61 / 3.70); the walk-start yaw peak at
      4.18 s is 0.196 with the hold and 0.241 without. Travel 3.018 m vs 3.116 m (-3.2 %, limit 20 %).
      Landing grace: first entry 1.28 s, FIXED_STAND 3.30 s, 0.70 s before the 4.0 s command.
      Pre-entry determinism: 63 rows identical to the C1d hold-off baseline in both runs
      (`stance_hold_qualification/pre_entry_d6_20260917T181650Z.json`).
      Claim-boundary note: with the crossfade the entry step applies V12's own PD law with Kd stepped to 1.0, so
      AC1's literal torque-continuity clause does not describe the entry step; the torque-matched seed is the
      exact end point of the blend.

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
- [x] C1b Rerun the hold-on stand (60 s); hold-off baseline reused from C1. Done 2026-09-17 13:23-13:26 UTC:
      `isaac_runner/runs/stand_20260917T132323Z_hold_auto_ramp` (EXTERNAL_EPISODE_FINISHED, 25/25 hashes). AC3 pass (yaw ≤ 0.0043, drift
      1.8 mm, min foot 23.2 N), AC5 pass, **AC7 fail**: vertical speed 0.020 m/s (pass; the hop is gone,
      feet ≥ 20 N), but |yaw rate| 0.363 rad/s at 0.68 s (limit 0.15). The yaw now swings +0.34 / −0.36 with
      period ~0.35 s during the low-gain part of the ramp; with the immediate step it peaked at 0.30 and damped
      faster. The trace is identical to C1 up to entry (deterministic). Report:
      `stance_hold_qualification/stand_ab_ramp_20260917T132323Z_hold_auto_ramp.json`; figure `stand_ab/entry_ramp_compare.png`.
      C2 stays paused; next step needs Dr Sun (damping at entry, see the lead's report).
- [ ] C2 Two-goal series with `scan_04` and `--stance-hold auto`: 8 episodes (6 cancel at 0.40 m, 1 at 0.45 m, 1 at
      0.50 m), reviewed like the SCAN series (41 checks, D11-style stop rule), with walk videos.
- [ ] C3 Host state after; containers and ports clean.

## D. Report

- [ ] D1 `RESULT.md` (AC3-AC6), figures (the stand A/B yaw and drift traces, the per-episode mode timelines) and
      a private Artifact page.
- [ ] D2 Dr Sun decides whether `--stance-hold auto` becomes the default for later pilots.
- [ ] D3 Commit (local-only bytes in the manifest), journal, hot zone, archive.
