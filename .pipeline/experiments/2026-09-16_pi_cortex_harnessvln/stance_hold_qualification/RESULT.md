---
origin: ai_with_source_check
reviewed: false
date: 2026-09-18
task: .trellis/tasks/09-17-isaac-runner-stance-hold
machine: gpu5070ti (Isaac Lab on the RTX 5070 Ti); analysis local
---

# Isaac runner stance hold: qualification result

The Isaac runner can now hand the joints from the V12 policy (`model_149999.pt`) to a PD stance hold when the
command is zero, and hand them back when a command arrives. This file reports the acceptance criteria of
`.trellis/tasks/09-17-isaac-runner-stance-hold/prd.md` for the selected entry, `xfade1s` (PRD D6). It also covers
the entry variants that failed before it.

## Verdict

| Criterion | Status | Evidence |
| --- | --- | --- |
| AC1 state-machine unit tests | pass, with a note | `isaac_runner/test_stance_hold.py`; isaac_runner 211 tests pass. Note: the torque-matched seed (continuity ≤ 1e-6 Nm) is still built and tested. With the D6 crossfade, however, the entry step itself applies V12's own PD law with Kd stepped 0.5 → 1.0. The literal "torque continuous at entry" clause therefore no longer describes the entry step |
| AC2 patch, `off` path unchanged | pass | `materialize_runner_patch.py --check` clean; off-path equivalence and mock-step tests; patched runner `0649747e…`. In both D6 walk runs, the 63 rows before the first entry are identical to the hold-off baseline |
| AC3 stand A/B, 60 s | pass | C1 `stand_20260917T125239Z` over 55.7 s of FIXED_STAND: \|yaw rate\| ≤ 0.0038 rad/s, drift 2.5 mm, speed ≤ 0.013 m/s, min foot force 23.0 N, \|pitch\| ≤ 2.8°. Hold off, same window: 0.143 rad/s, 3.4 cm, 0 N, 6.6°. Run with the step entry (see "Disclosed changes") |
| **AC4 two-goal series, 8 episodes** | **pass** | 8/8 passed the unchanged 41 checks (one-sided 95 % lower bound 0.688). The hold-off SCAN series was 7/8 (0.529) |
| AC5 transitions | pass | Every hold-on run (2 stand, 5 walk, 8 two-goal): no non-foot contact, \|roll\| and \|pitch\| ≤ 10° in REJOIN, no torque clip at entry or rejoin |
| AC6 claim boundary | stated | Section "Claim boundary" below |
| **AC7 entry smoothness** | **pass with the post-result amendment (D7); fail as frozen** | Selected `xfade1s`: D6 walk 3/3 entries pass (max 0.087 rad/s). C2 series 30/30 with the amended window; as frozen 29/30, because episode 6's window caught a restart (0.174 rad/s). Earlier entries fail under both rules (no restart in their windows): C1 step (hop, 0.30 rad/s, 0.21 m/s), C1b ramp (0.363), C1d ramp / step1 / step2p5 |
| AC8 scripted walk | pass (`xfade1s`, `xfade2s`) | `walk_d6_20260917T181650Z.json`; the D5 rule selects `xfade1s`. No C1d variant passed AC8 b |

**Post-result change.** AC7 was amended by Dr Sun on 2026-09-18, after the C2 result was known (PRD D7). The
entry window now ends at the restart, the first row after entry whose mode is neither STAND_TRANSITION nor
FIXED_STAND, and that row is excluded. As frozen before the results, AC7 fails in C2 episode 6. Both verdicts are
reported everywhere below. Dr Sun also made `--stance-hold auto` with `xfade1s` the launcher default (PRD D8).

## What the evidence shows

1. **The hold stands still.**
   - In the 60 s stand, FIXED_STAND held yaw at or below 0.0038 rad/s and drift at 2.5 mm, where V12 alone
     reached 0.143 rad/s and 3.4 cm (`stand_ab/stand_ab_traces.png`).
   - In the scripted walk the xfade1s hold reached FIXED_STAND at every stop. Over the last 2 s of each walking
     stop, tail yaw was 0.0011–0.0017 rad/s and drift 0.12–0.31 mm; hold off gave 0.065–0.117 rad/s and 1.9–4.3 mm
     (figure 2).
2. **The entry was the hard part, and the crossfade fixed it.**
   - An immediate Kp 20 → 60 step made the body hop (C1). V12's actuator applies position targets 3 substeps
     late, while gains act at once.
   - A 0.5 s gain ramp removed the hop but swung the yaw to 0.363 rad/s (C1b).
   - Stepping only the damping (C1d) failed at one or more entries in every variant.
   - The D6 crossfade blends V12's live PD command into the hold command over 1 s, with Kd 1.0 from entry. It kept
     every walk entry at or below 0.087 rad/s, and each maximum was the yaw already present on the entry row
     (figure 1).
3. **Restarts are gentler with the hold.**
   - In the walk, max |pitch| in the 1 s after each start was 4.27 / 2.28° (hold off 5.61 / 3.70°), and the
     first-start yaw peak was 0.196 rad/s (hold off 0.241).
   - In the two-goal series, max |yaw rate| in the 1 s after a resumed command had a median of 0.165 rad/s and
     a max of 0.197 over 24 restarts. The hold-off series gave 0.201 and 0.341 (figure 3, right).
4. **The hold does not change the two-goal stop check.**
   - The review's still window is the 1 s before each terminal. It runs from 0.10–0.38 s to 1.12–1.40 s after the
     zero command.
   - In that period V12 still drives the joints (STAND_SETTLING, waiting for the entry gates), plus the start of
     the crossfade.
   - All 24 still-window peaks fall in STAND_SETTLING. The median still-window max |yaw rate| is 0.120 rad/s with
     the hold and 0.121 without (figure 3, left).
   - No two-goal stop lasted long enough to reach FIXED_STAND (figure 4). The 8/8 pass is therefore not evidence
     that the PD hold keeps the robot still during the review windows.

## Two-goal series (8 episodes, `scan_04`, `xfade1s`, 2026-09-17 18:41 – 2026-09-18 03:14 UTC)

Driver `run_hold_series.py`, ledger `hold_series/series_ledger.jsonl`, report `series_d7_20260918.json`
(as-frozen report: `series_d6_20260918.json`). Every episode passed returned hashes, the walk review and both SCAN
workspace gates. GPU peak was 7086–7134 MiB, sim time 15.9–16.4 s and wall time 21.4–22.4 s. The first
(landing) entry came at 1.28 s in all eight.

| Ep | Cancel at | Measured | Checks | Arrival XY error A / B (m) | Entries / exits | Time to hold after each stop (s) | Still-window max \|yaw\| (rad/s) | AC7 as frozen | AC7 amended |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.40 m | 0.415 m | 41/41 | 0.200 / 0.188 | 4 / 3 | 0.62 / 0.44 / 1.12 | 0.144 / 0.145 / 0.121 | pass | pass |
| 2 | 0.40 m | 0.419 m | 41/41 | 0.188 / 0.175 | 4 / 3 | 0.62 / 0.44 / 0.54 | 0.125 / 0.122 / 0.143 | pass | pass |
| 3† | 0.40 m | 0.412 m | 41/41 | 0.190 / 0.174 | 4 / 3 | 0.62 / 0.38 / 0.56 | 0.128 / 0.094 / 0.103 | pass | pass |
| 4 | 0.40 m | 0.401 m | 41/41 | 0.181 / 0.160 | 4 / 3 | 0.90 / 0.44 / 0.52 | 0.134 / 0.116 / 0.143 | pass | pass |
| 5 | 0.40 m | 0.420 m | 41/41 | 0.185 / 0.145 | 3 / 3 | 0.62 / 0.42 / — | 0.125 / 0.105 / 0.135 | pass | pass |
| 6 | 0.40 m | 0.412 m | 41/41 | 0.196 / 0.182 | 4 / 3 | 2.22 / 0.38 / 0.62 | 0.109 / 0.096 / 0.094 | **fail** (0.174) | pass (0.063) |
| 7 | 0.45 m | 0.484 m | 41/41 | 0.181 / 0.152 | 3 / 3 | 0.54 / 1.04 / — | 0.109 / 0.113 / 0.113 | pass | pass |
| 8 | 0.50 m | 0.522 m | 41/41 | 0.174 / 0.177 | 4 / 3 | 0.84 / 0.44 / 0.52 | 0.077 / 0.119 / 0.135 | pass | pass |

Reading the table:
- **Stops** are the cancel, arrival at A and arrival at B.
- **Still-window limit:** 0.15 rad/s.
- **"—":** the episode finished before the gates allowed an entry.
- **Exits:** all 24 exits went from STAND_TRANSITION through REJOIN (0.25 s blend).
- **Restarts inside the entry window:** in 9 of the 30 windows the planner resumed within 1 s of entry. Up to that
  restart, every window stays at or below 0.098 rad/s and 0.024 m/s.
- **† Episode 3** is marked because of how it was collected, not its result. The local driver died with the Claude
  session after the remote worker had finished; the remote result was final, passed, with exit codes 0.
  `recover_interrupted_episode.py` collected it with the launcher's own remote-only collect steps and reviewed it
  unchanged; physics did not re-run. Only the worker's SSH stdout log (`02_remote_worker.log`) is missing. Its
  ledger line carries `recovered_after_driver_interrupt`, and the executed script version is kept byte for byte
  (`recover_interrupted_episode.executed_10993936.py`).

### Episode 6 and the AC7 amendment

1. **The hold entered late.** At the cancel stop (first zero-command row at 4.46 s), STAND_SETTLING waited
   2.2 s, mostly for the support-balance gate: 84 of 110 rows, 24 for linear speed, 2 for angular speed.
2. **The entry was calm.** The hold entered at 6.66 s, and |yaw rate| stayed at or below 0.063 rad/s.
3. **The planner resumed 0.18 s after entry.** It resumed goal A at 6.84 s (step 341), the first REJOIN row, while
   the crossfade weight was still small (Kp 22.7).
4. **The restart set the peak.** V12 restarted walking, and |yaw rate| reached 0.174 rad/s at 6.92 s inside REJOIN;
   the command asked for 0.019 rad/s. That is a normal V12 restart value. Across the hold-off series, restarts reach
   a median of 0.201 rad/s within 1 s.
5. **The two windows differ.** The frozen window ran a fixed 1.0 s after entry, so it scored the restart. The amended
   window ends at 6.84 s (figure 5). Amended: 0.063 rad/s and 0.013 m/s, pass. As frozen: 0.174 rad/s, fail.

## Disclosed changes to the plan

- **D4, before the C1b rerun:** after the C1 hop, a 0.5 s gain ramp at entry, and AC7 added.
- **D5, before any walk run:** the scripted walk, AC8, the side camera and the entry-damping variants.
- **D6, before its walk runs:** the crossfade entry, plus a 1.0 s landing grace for the crossfade variants. The
  grace is a design choice, not an exclusion; AC7 and AC8 still apply to the landing entry.
- **D7, post-result:** the AC7 window ends at a restart (above). AC8 b keeps its literal 1.0 s window.
- **D8:** `run_two_goal_pilot.py` and `qualify_stand_runner.py` default to `--stance-hold auto`. The entry
  variant then resolves to `xfade1s`; with `--stance-hold off` it resolves to `ramp`, the only one allowed there.
  - Packages prepared earlier keep their recorded meaning: a missing field means `off` / `ramp`.
  - The runner patch default stays `off` and its bytes are unchanged, because the launchers always pass the flag.
  - The SCAN-fix series driver and the point-cloud probe (`pointcloud_display/run_probe.py`) pass
    `--stance-hold off` explicitly. `P2B_RESULT.md` notes the flag for reproducing P2B.
- **Thresholds**, re-frozen before each run set:
  `fb8f9204…` → `12373448…` (AC7) → `683a8ca6…` (AC8) → `0be59927…` (descriptive) → `34c15fe6…` (D7, post-result).
  Every earlier file is kept in `isaac_runner/stance_hold_thresholds_history/`. No limit changed.
- **AC3 was not repeated with `xfade1s`.** The 60 s stand ran with the C1 step entry. D6 changed only the entry,
  and the FIXED_STAND law is the same. The xfade1s hold is covered by the walk stops (up to 5.5 s): yaw ≤ 0.0017
  rad/s over the last 2 s.
- **Episode 3** was collected after the driver interrupt (above). Episodes 4–8 ran from `--from-episode 4`.

## Findings beyond the criteria

- **The review's stop check measures V12's own settling.**
  - The stop dwell sits inside STAND_SETTLING, so the hold cannot change its margin.
  - The worst hold-on stop was 0.145 rad/s against the 0.15 limit, which leaves the same margin as hold off.
  - An earlier entry would need looser gates, which trade against the entry kick. That, or a longer dwell before
    the terminal, is a separate decision; nothing here changes it.
- **Time to hold after a walking stop was 0.38–2.22 s**, set by the settle gates (support balance, linear and angular
  speed, four-foot contact).
- **The body was quiet before every walk entry** (angular speed ≤ 0.17 rad/s), so a stricter body gate would not
  have fixed the C1d entries (survey `.pipeline/survey/2026-09-17_rl_pd_stance_hold_switch_survey.md`).

## Claim boundary

- Simulation only: Isaac Lab on the 5070 Ti host, V12 `model_149999.pt` in the Isaac runner. There is no
  physical-robot result, and this is not a deployment fix. The `machine-dog` deployment program is unchanged
  (PRD D1).
- One known-map two-goal route on a flat platform with simulator-truth pose, and one scripted straight walk. No
  slopes, obstacles, pushes, SLAM or language navigation.
- N = 8 two-goal episodes, 8 passed (one-sided 95 % lower bound 0.688). There are three walk-stop sequences and
  one 60 s stand per configuration.
- AC7 passes only under the post-result amendment. As frozen before the results, AC7 fails in one C2 window.
- Evidence label: integrated. The hold works inside this repository's Isaac runner. It is not `validated`, because
  AC7 as frozen failed and the pass rests on a post-result amendment.

## Report and reproduction

- Page: https://claude.ai/artifact/LbF8JD4XWmnsfgvnDbUVMM (private), built from `report/index.html`. Figures come from `report/figures/` and
  `stand_ab/stand_ab_traces.png`. Videos come from `walk_ab/walk_d6_side_view.mp4` and each two-goal run's
  `walk_review/walk_review.mp4`, published as `videos/e0N.mp4`.
- Figures: `make_result_figures.py` writes `report/figures/fig1…fig5`. The stand figure is `stand_ab/stand_ab_traces.png`.
- Analyzer (`isaac_runner/analyze_stance_hold.py`, thresholds `34c15fe6…`):
  - `stand`: `stand_ab_d7_20260917T125239Z.json`, `stand_ab_ramp_d7_20260917T132323Z_hold_auto_ramp.json`;
  - `walk`: `walk_ab_d7_20260917T145650Z.json`, `walk_d6_d7_20260917T181650Z.json`;
  - series: `series_report.py` → `series_d7_20260918.json`.
- Runs:
  - `isaac_runner/runs/stand_20260917T125239Z_hold_{off,auto}`, `stand_20260917T132323Z_hold_auto_ramp`;
  - `isaac_runner/runs/walk_20260917T145650Z_*` and `walk_20260917T181650Z_*`;
  - `isaac_runner/two_goal_runs/two_goal_*_hold_e0{1..8}`.
- Local-only bytes (inputs, the PCT runtime, videos) are listed in `../LOCAL_ONLY_BYTES.sha256`. Point clouds and
  third-person video of the two-goal runs stay on the host (`--remote-only-bulk`, D9 of the pilot).
