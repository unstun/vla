# v49 results: bounded local solve, acceptance failed

**v49 is frozen and tested, but must not be treated as a validated candidate.**
The qualified execution `v49_realtime_trial02` removed the observed 100–1000 ms
solve spikes, but exceeded the 33.3 ms cap three times, reduced useful planning
to 2.883 Hz, and exposed a timeout-to-backend stop-protocol error. No arrival or
formal terminal hold was recorded. v48 remains the previous experimental
reference; the last validated navigation condition remains v3's empty-floor trial.

## Full-stack result

Both trials use gpu5070ti, the same historical Building scene, 6-CPU native quota,
CPU physics graph, factory PD/stance startup, geometric LiDAR and target RTF 1.
Both record 89.962 native seconds. These are different physical trajectories;
latency differences are not a paired live-input causal experiment.

| Measurement | v48 trial01 | v49 trial02 |
|---|---:|---:|
| Attempt rate, wall time | 15.859 Hz | **3.825 Hz** |
| New-plan rate, wall time | 15.761 Hz | **2.883 Hz** |
| Completed rounds | 1,311 | 334 |
| Accepted new plans | 1,303 | 251 |
| Freshly validated continuations | n/a | 3 |
| Timeout emergency-stop commands | n/a | 80 |
| Median round time | 3.092 ms | 4.271 ms |
| P95 round time | 126.496 ms | 25.739 ms |
| P99 round time | 207.175 ms | 30.440 ms |
| Maximum round time | 1,090.481 ms | **37.998 ms** |
| Rounds >=100 ms | 158 | **0** |
| Rounds >33.333 ms | 440 | **3** |
| Measured XY path length | 28.479 m | **1.432 m** |
| Navigation RTF | 0.95282 | 0.89518 |

v49 has 18 whole rounds above 25 ms. All 334 instrumented budget calls were also
checked independently; their maximum is 37.980 ms, with no call >=100 ms and
three above 33.333 ms. The whole nominal round includes wrapper/logging overhead.
The largest overrun is detected at `after_input_refresh`; the other two are
at `raw_contributor`. Cooperative checkpoints cannot interrupt atomic sensor
application or scheduling delays. This run does **not** validate a strict cap.

The attempt-rate definition matches the earlier plots: `(starts-1)/(last-start -
first-start)`. New-plan rate here uses successful outcomes divided by the full
first-start-to-last-completion exposure for both versions (a small denominator
difference from the earlier v48 report's 15.757 Hz). Continuation is separate:
3 / 87.077 s = 0.0345 Hz. Short 30 Hz bursts do not establish sustained planning.
The last successful new plan starts at simulation time 35.412 s. Later attempts
mostly emit timeout stops following global refresh. Raw command publication is
30.905 Hz over the observed planning span, including extra emergency emissions;
this is not an improved controller timer rate. Global refresh is 1.00006 Hz over
its retained 50-event history.

## Stop-protocol defect — acceptance blocker

The new FSM sends a rejected admission with `native_solve_timeout`, then publishes
the original emergency B-spline. The unchanged backend handler recognizes only
`native_replan_exhausted` for closing the same-owner command gate and entering the
existing verified stop flow. The new reason is ignored by that branch. At the
end of trial02, the backend gate is `open`, `hold_ack=false`, `stop_flow=null` and
there is no terminal result. Physical stillness and an emergency message do not
substitute for the required controller-hold/measured-stillness acknowledgment.
Repeated global refreshes therefore keep restarting planning.

This is an implementation error in v49, not an accepted change to the safety
contract. `analysis/check_stop_protocol.py` executes the exact frozen handler
AST with the same owner: the new reason produces zero gate-close/zero-command
calls; the original reason produces one of each. The one-line candidate fix is
saved as `analysis/proposed_stop_protocol_fix.patch` and has **not** been applied
to frozen v49. The component stop test checked publication and identity but
mistakenly treated receiving the notice as proof that the backend gate closed.
A future version must exercise the real backend handler and terminal stop flow.

Goal XYZ/yaw, route admission parameters, PVA/dynamics/minimum-cruise gates and
occupancy/support decision rules retain the parent values/logic. The new stop
protocol fails end-to-end safety acceptance despite that preservation.

## Implementation and component evidence

One shared monotonic deadline gives compute 20 ms and final checks/recovery up
to 25 ms total; retries cannot reset it. Search, optimizer, retiming and collision
queries have cancellation checkpoints. L-BFGS workspace cleanup survives thrown
timeouts. Old trajectory/progress rollback precedes timeout recovery, and no
partial candidate is published. Continuation requires exact ownership and fresh
full remaining-curve validation, without restamping.

Final build03 and test03 pass: 34 native checks, 48 cache checks, 94 warm checks,
76 deadline fixture checks, exact cold geometry on both recorded v32/v33 maps,
and 3,000 instrumented L-BFGS cancellations with no outstanding allocation.
These component passes do not override the live acceptance failure.

Native source: 99 files; installed build: 517 files; original source freeze:
6,590 files. The patch/materializer reproduces the native source exactly. Inline
review/checks were used; no independent agent review was performed.

Attempt01 expected uncached continuation but its fresh curve check exhausted
the reserve and correctly stopped. Its full source and evidence are retained.
Attempt02 passed; build03 adds malformed-spline rejection before duration access.
The pre-physics trial01 failed because `native_graph.py` was missing. The launcher
was added with only its three v48→v49 identity-label occurrences changed, recorded
in `launch_supplement.json` and `launch_source/`; the original frozen manifest and
all of its bytes remain unchanged. Trial02 passed execution/copyback gates and
failed the timing, stop-contract and navigation acceptance gates above.

All **909 original trial02 artifacts (1,321,643,904 bytes)** are returned locally
and match the remote SHA-256 manifest. Trial01's 57 original pre-physics failure
artifacts and all three build/test attempts are also preserved. Native state
copyback is verified; this does not establish terminal navigation acceptance.

## Artifacts

- [Updated time-series comparison](analysis/time_series/v48_v49_planning_time_series.png)
- [PDF](analysis/time_series/v48_v49_planning_time_series.pdf) · [SVG](analysis/time_series/v48_v49_planning_time_series.svg)
- [Metrics and definitions](analysis/metrics.json)
- [v49 round data](analysis/time_series/v49_round_latency.csv) · [rolling frequency](analysis/time_series/v49_frequency.csv)
- [Stop protocol reproduction](analysis/stop_protocol_result.json)
- [Original trial artifact manifest](trials/attempt02/return_manifest.json)
- [Local return verification](analysis/return_verification.json)

No frozen v49 implementation is repaired in place. A v50 decision is pending
Dr Sun's response; it must preserve these failed results and address both the
stop protocol and the measured deadline overruns before claiming acceptance.
