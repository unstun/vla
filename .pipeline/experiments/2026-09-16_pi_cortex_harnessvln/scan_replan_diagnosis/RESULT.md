# SCAN Resubmit Failure: Confirmed Native Mechanism

Date: 2026-09-16. Stage: experiment + analysis.

The direct cause of the captured candidate rejection is confirmed in the
currently frozen SCAN implementation: polynomial initialization samples only
times strictly before the polynomial end, then uses acceleration at the last
sample as the endpoint derivative. The requested true endpoint acceleration
is zero. At the failed stopping position, this substitutes about 1.778 m/s^2
for zero; reparameterization/refinement retains that endpoint value and the
unchanged final 1.5 m/s^2 dynamic gate rejects the candidate.

## Direct runtime evidence

The real C++ `SCANPlannerManager::reboundReplan` was compiled against scan_03
and its actual installed libraries in the pinned Foxy image. Each case starts
with a fresh manager and an empty grid, with no cancellation, controller,
sensor publisher, Isaac process or robot. Four recorded start/goal-derived
cases were each repeated three times with seed zero.

The failing input reproduces the original warning exactly to its printed
precision: `acceleration at t=3.500 is 1.567 > 1.500`. Cancellation is therefore
not necessary to produce this rejection; it exposes a problematic restart
position in the full pilot.

| Derived case | True polynomial end T (s) | Last sample t (s) | Wrong endpoint acceleration (m/s^2) | Original result |
| --- | ---: | ---: | ---: | --- |
| Successful actual4 resume | 1.701096 | 1.600000 | 1.477624 | 3/3 passed |
| Failed GPU-probe resume | 1.730701 | 1.600000 | 1.778131 | 3/3 failed |

The approximately 5 cm difference in stopping position changes the fractional
interval omitted at the endpoint. The successful case is just below the hard
gate. This explains why a previously successful pilot did not establish
repeatable interruption/recovery behavior.

For the failed case, direct in-function instrumentation records:

- Last sampled acceleration: 1.778131330 m/s^2; true endpoint acceleration:
  approximately 1.42e-14 m/s^2.
- Reallocation ratio: 3.045183476. The spline duration increases from 1.6 to
  3.563376137 seconds, yet refined endpoint acceleration is 1.778376817 m/s^2.
- Refinement optimizes internal control points while retaining boundary
  information. Making the trajectory longer therefore does not eliminate the
  incorrectly supplied endpoint derivative.
- Both initial-position cases and the successful-resume case pass 3/3 under
  the original implementation; only the failing-resume fixture fails 3/3.

## Single-variable diagnostic intervention

The candidate changes one behavior line in an isolated manager copy:

```diff
- start_end_derivatives.push_back(gl_traj.evaluateAcc(t));
+ start_end_derivatives.push_back(gl_traj.evaluateAcc(time));
```

`t` is the last sample before the endpoint; `time` is the true polynomial end.
All limits, fixture arguments, optimizer settings, libraries and diagnostic
logging remain identical. No heartbeat deadline or safety check is relaxed.

| Same failing-resume input | Original | Diagnostic candidate |
| --- | ---: | ---: |
| Native successful plans | 0/3 | 3/3 |
| Refined sampled maximum acceleration (m/s^2) | 1.778377 | 0.590245 |
| Final acceleration gate (m/s^2) | 1.500000 | 1.500000 |

All four candidate cases pass all three repeats, totaling 12/12. Their sampled
maximum accelerations stay below the unchanged gate. `comparison.json` passes
nine checks covering the observed failure/pass split, identical case commands,
unchanged limits, source equality, the one-line behavioral difference, returned
hashes and container cleanup. An independent read-only subagent review agrees
with this diagnosis and its validation boundary.

## Evidence and reproduction

- Source trigger: `p2b_execution/builds/scan_03/src/plan_manage/src/planner_manager.cpp`,
  polynomial sample loop and terminal derivative construction, lines 150-171.
  This attribution is to the frozen implementation used here; it is not a
  verified claim about an unmodified official upstream repository.
- Original run: `runs/native_original_20260916T180500Z/`.
- Candidate run: `runs/native_true_end_20260916T180700Z/`.
- Each run matched 67 native source files, 380 installed files and 15 diagnostic
  package files before execution. Both sets of 16 returned artifact hashes
  match locally; the native source and package remained unchanged during runs.
- Direct stage logs use `[DEBUG-scan-0916]`. Auxiliary `POLY_INIT_*` output is a
  mirrored calculation, not the acceptance oracle; the real manager return and
  in-function diagnostics are the evidence used in `analyze_native.py`.
- Each case took about 0.114 wall seconds in the original loop. Builds used the
  original Release setting; complete build/command logs and executable hashes
  are retained in each run's `returned_artifacts/`.

Recheck the returned evidence locally with:

```bash
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_replan_diagnosis/analyze_native.py
```

`instrument_manager.py` regenerates either isolated source condition.
`native_worker.py` records exact container build and replay commands.
`container_cases.py` enforces a 20-second per-case ceiling. Existing run
packages are immutable; use a new run directory to execute new conditions.

## Remaining boundary

The production materializer, scan_03 and all previous pilot packages remain
unchanged. This investigation verifies a candidate correction at the native
planner boundary, not a corrected complete navigation stack. The fixtures use
recorded PCT-request poses plus the frozen body-height offset, not an exact
capture of every native argument or the live occupancy map.

The candidate still uses the original point sampling and least-squares spline
fit. Its failed-resume fixture ends approximately 3.5 cm from the route endpoint.
Before adopting a production repair, verify endpoint geometry, nonempty-map
collision checks, random initialization, subsequent replans and continuous
Isaac cancellation/arrival with the existing criteria. No physical deployment
claim follows from this CPU-only diagnostic.
