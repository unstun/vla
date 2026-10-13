# Original-system stop/recovery investigation

Stage: experiment + analysis. **Full recovery repair remains unaccepted.**
The pre-MPPI native baseline is v114. The earlier MPPI adaptation comparison
used diagnostic v122; their counts must not be merged.

## Direct answer and closed physical results

All runs below used gpu5070ti, Linux x86_64, the pinned Ubuntu 20.04/Foxy image,
CPU Newton, the original Building corner scene, original policy and original
sensor, collision, freshness and physical-stop criteria. No robot was actuated.

| Set | Original v114 | Candidate | Falls | Decision |
| --- | --- | --- | --- | --- |
| Three initial unchanged v114 diagnostics, host v125 | 1/3 arrivals | None | 0 | Original instability reproduced |
| Fixed six-per-arm v128 comparison, shared host v128 | 2/6 | v128: 2/6 | 0 in both arms | Notification repair does not establish mission reliability |
| Fixed six-per-arm v131 comparison, shared host v131 | 2/6 | v131: 1/6 | Original 0; candidate 1 | Candidate not adopted |
| Three fixed v133 diagnostic pilots | No new controls in this set | 2/3 | 0 | Pilot gate failed; no new final comparison |

The v133 successful paths were 26.532 and 26.533 m. Its failed pilot stopped
after 16.404 m. Do not compare its selected diagnostic stage to the six-per-arm
sets as a controlled success-rate estimate. All pilots and failed trials remain
available; none was replaced. All execution, copyback and retention gates passed.
A successful process/retention result is not a successful navigation result.

## Isolated changes and verified boundaries

| Version | Change from its frozen parent | Direct checks | Physical boundary |
| --- | --- | --- | --- |
| v128 | Start from native v114/host v125. Retain negative safety evidence and expose failure on the next control tick instead of returning normal zeros indefinitely. | Two actual-plugin regressions fail against original v114; 38 component tests pass after repair. Late positive proof cannot revoke a stop latch. | Pilot arrived; final comparison 2/6 versus 2/6 fails reliability gate. |
| v129 | Allow 10 s for measured stop and 11 s for the BT service response. | Original captured stream needs 5.28 s; old 4 s gateway fails. New gateway passes; missing proof and cancellation still fail. Actual BT transport waits for a 5.3 s response. | One successful pilot, which did not itself exercise the longer settling case. |
| v130 | Use the current due measured body for new-reference search, rather than stale/uninitialized local start state. | Actual native callback/AStar origin witness changes 0/4 to 4/4, including exact due/future ordering. Unknown map remains rejected. | One successful pilot with two recovered stops; no reliability acceptance. |
| v131 | Bound outer mission recoveries at 6, keeping measured-stop gating. The shared recorder observes the existing stop-proof topic read-only in both arms. | Actual installed RecoveryNode/WaitForScanStop tests: success on fourth attempt after three proved stops; persistent failure ends after seven attempts; missing proof ends after one attempt. | Final comparison fails: 1/6 arrivals and one fall. No adoption. |
| v132 | Record the exact new-reference rejection branch, time and heading validity; decisions unchanged. | Six reconstructed-map verdict/frontier cases agree with v131. | First diagnostic fails at 23.492 m and captures five rejected references. It is a diagnostic, not a repair. |
| v133 | Drain/adopt original arrived and due inputs after unsuccessful goal-neighborhood search, before fallback reference queries. | Actual installed FSM/helper/map/queue regression now consumes a newly due pose; absent data and a one-nanosecond future pose remain rejected. | Three pilots: two arrivals, one failure, no falls. Overall repair unaccepted. |

Every version built all 14 packages and passed 38 native component tests,
host receipt/parameter checks, actual writer-ownership checks and a 10 s native
graph check. Frozen source-pair counts are 2,831 / 2,866 / 2,901 / 2,935 /
2,970 / 3,004 for v128–v133; each binds 618 runtime inputs. These checks do not
constitute complete navigation or Jetson acceptance. The original 36-test
baseline lacks the two v128 regressions. The first red harness attempt also
had a fixture assertion error; it is retained, and red02 isolates the real bug.

No MPPI adaptations are included in this repair lineage. Original source,
all frozen versions and the previously retained v122/host-v125 metadata remain
unchanged. The broader v48 reference and main Trellis task remain open.

## What the retained failures show

**Notification delay is real and repaired at the callback boundary.** In the
v128 comparison, original asynchronous negative-safety stops took 9.558–10.313 s
to abort FollowPath; v128 took 8.012–23.517 ms. In the v131 comparison, original
stops took 9.768–10.119 s and the candidate took 2.784–25.579 ms. Ordinary goal
holds and cancellation retain zero-command semantics and measured ownership
release. Faster notification alone did not produce reliable missions.

**Measured stop is not guaranteed by a zero command.** The v128 candidate04
recorded stream cannot establish the original continuous one-second stop window
until about 5.273 s. That motivates v129's wait budget, without changing the
0.01 command norm, 0.1 m/s horizontal speed or 0.15 rad/s yaw-rate limits.
Replaying every applied sample is a necessary-window bound, not a reconstruction
of exact gateway polling/DDS order. All 38 replacement owners in the v131 batch
and all 9 in the v133 pilots have matching recorded gateway stop proofs before
new-route delivery.

**Live reference admission can expire its inputs during computation.** In v132,
generations 3/5/7 start with a valid heading, spend 167.883/146.802/151.266 ms,
and reject sample zero with a nonfinite heading after the body data expires.
Generations 4/6 reject with observation ages about 254.860 ms, beyond the
unchanged 250 ms limit. The old fallback never drains already-arrived inputs
again after the search. v133 adds that refresh. Its controlled regression uses
a stubbed unsuccessful search with a 120 ms ROS-clock advance and a constructed
future body sample; the actual FSM, map, due-body queue and freshness rules run.
This is a component regression, not a reproduction of the entire physical scene.

The earlier reconstruction of 410 exact recorded scans accepts the recorded
route in about 0.6 ms when inputs are fresh. It does not restore the original
asynchronous map revision/DDS batching and therefore did not reproduce the live
failure or justify a cache optimization. v133's third pilot accepts references
after 106 and 130 ms with fresh body data, but also rejects a reference when the
latest adopted observation is still about 270 ms old. One refresh does not
manufacture a fresh completed map; that rejection must remain.

**There is a separate posture/geometry problem.** v131 candidate06 admits all
seven reference generations, but cold trajectory starts are repeatedly rejected
at the starting geometry while the body remains tilted about 23–28 degrees in
STAND_SETTLING. It is not a lost route. In the fallen candidate05, tilt is already
23.4 degrees at 37.991 s, 44.6 degrees at 38.790 s and 54.2 degrees at 38.950 s;
native stop is at 38.970 s and fall detection at 39.090 s. The tilt precedes the
stop; this chronology does not identify the dynamics cause or prove a regression.

The failed v133 pilot similarly tilts to about 30–33 degrees after turning and
cannot complete the original stop window: longest continuous qualifying interval
is only 0.720 s in the retained final-stop stream, versus the required 1 s.
Increasing retry counts or releasing ownership without proof would not repair
this condition. Its stop replay includes yaw-rate violations and later stale
command records after the mission failure; see the raw predicate counts.

There is also an initial map-readiness race: two v133 pilots reject the first
reference with observation stamp zero, then accept after the first recovery.
A first route must eventually wait for a valid local map rather than treating
an unready map as permanent bad geometry. This behavior is not repaired yet.

## Decision and next boundary

Do not adopt v131 or v133 as a stable system. Keep the tested isolated fixes and
all failed evidence available, but do not claim the original stop/recovery
problem is fully solved. The next investigation must separate initial local-map
readiness from turning/settling posture and native start-geometry rejection.
Do not tune away collision, freshness or stillness guards, or assume that a
longer wait fixes an unstable body. Changes to speed, policy, footprint or
locomotion recovery need their own explicit design and acceptance boundary.

The v131 comparison's median run P99 is 83.279 ms versus 26.125 ms for original
v114; median maxima are 301.683 versus 194.178 ms. This is not a tail-performance
improvement. Small counts (Fisher two-sided p=1.0) do not establish equivalence,
a regression attribution or general success rates. Only this simulator scenario
was exercised; no Jetson, real-robot or training result is claimed.

## Source and storage

- Local source of truth: `/Users/sun/tongbu/study/phdproject/vla`.
- Remote execution/raw root: `/data/sun/vla_mppi_20261009` on gpu5070ti.
- Pinned image: `sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4`.
- `foxy_reference/` retains installed Foxy 0.4.7 XML/package provenance and
  license. Its regular recovery tree uses outer 6; its round-robin tree uses
  outer 2 and inner 4. These are different examples, not identical custom behavior.
- `results/verified/MANIFEST.json`: 315 returned compact files, 11,052,868 bytes;
  every local byte/hash verified, plus original source/install re-verification.
  All raw tree indexes for 32 later trials match their retained files.
- `results/original_storage/`: the three earlier original-v114 raw archives
  match their original recorded archive digests. Total physical trials retained: 35.
- `return_verification.json` binds both returned bundles. Heavy data, builds,
  policies, reconstructed inputs and failed attempts stay remote. Regenerate
  compact data with the versioned/audit runners; original archives use the
  retained v51 restoration instructions. No automatic commit or lock removal.
