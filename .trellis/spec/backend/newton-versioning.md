# Local Newton integration versions

## 1. Scope

Dr Sun designated the delivered empty-floor system as v3 on 2026-09-27.
Subsequent logical code/configuration changes increment the integer version.
This number is separate from native SCAN candidate numbers and Git HEAD.

## 2. Signatures

`run_local_episode.py --integration-version v4` checks
`versions/v4/manifest.json` before starting processes. An omitted value uses
`versions/current.json` when present. `verify_integration_version(out, version)`
is shared with the Building control probe and copies the verified manifest into
the run as `integration_version.json`.

## 3. Contracts

Before editing, declare one behavior change and its parent. Before executing,
preserve every selected source/configuration byte under `versions/vN/source/`
with original repository-relative paths; record SHA-256 in `source_files` and
the parent difference in `changes.patch`. From v52, unchanged inherited bytes
may reference the already frozen parent's source snapshot through explicit
`snapshot_locations`, with its manifest hash pinned and both the current source
and snapshot bytes verified. Preserve v52-owned bytes in its own source snapshot;
do not duplicate older build/runtime trees merely to repeat their provenance.
Earlier physical runs and their
executed source copies remain immutable. The baseline v3 manifest records the
already accepted trial, not a new run or a clean repository release.

The manifest is frozen. Append results and attempts separately. A failed test
does not license edits under the same frozen version; the next logical repair
uses vN+1. Do not change current source files while a process uses them. Reusing
unchanged code for another attempt retains the version but requires a new run ID.

`building_full` in v4 uses the complete archived Building/PCT map, the original
start/goal, actual geometric LiDAR, simulator body localization and the existing
factory/PD/RL controls. Static architecture has no added pedestrian. Use exact
triangle contacts via the existing Warp CPU solver and automatic contact budget.
Native empty-floor physics is not an equivalent Building collision condition.

## 4. Validation and errors

| Condition | Required outcome |
|---|---|
| Source differs from frozen manifest | Refuse launch; register a new version |
| Missing manifest or invalid version name | Refuse launch |
| New version, no actual trial | Record unvalidated/preparing, not working |
| Failure or timeout | Preserve all records under the attempted version |
| Versioned render | Display the physical run's integration version; keep source/frame hashes |

## 5. Cases

Good: v3 remains the accepted empty 12 m condition; v4 separately tests Building.
Base: multiple immutable test attempts may share unchanged v4 source.
Bad: replace v3 code or video with a Building failure and still call it v3.

## 6. Tests

`test_version_identity.py` checks exact manifest copy, rejects an actual source
mutation and rejects path traversal. The Building control probe checks measured
support, original PD ownership/gains, upright pose, ground-relative height and
motor force mapping. Navigation acceptance is separately reported by
`review_building_episode.py` after the common interface reviewer. Architectural
surface contacts are not scored by that reviewer; do not claim collision-free
navigation from it. Video verification requires full decoding, original state
times/hashes, frame hashes and direct visual inspection.

## 7. Wrong versus correct

Wrong: tag the dirty repository HEAD as the tested release, silently update
its code, or rename a failed trial to look successful.

Correct: freeze task-owned source bytes, bind execution to that identity and
report the precise accepted condition separately from the latest version.


## 8. Explicit parent selection may skip a rejected version

An increasing version number does not require the preceding integer as its
implementation parent. On 2026-10-01 Dr Sun selected v48 directly for v50 and
discarded v49's timeout approach. Preserve v49 and its failure evidence; record
`parent` and `native_source_parent` as v48 in v50's preparation and eventual
freeze. Verify copied source against the chosen parent's manifest. Keep the
runnable reference on v48 until a replacement passes its declared acceptance;
v50 is now frozen and component-qualified but failed full-run tail/continuity
acceptance. Do not relabel parent component results as new-version validation.
Check every runtime entry
file, including `native_graph.py`, before freezing an execution package.

## 9. Local curve capture and recovery displacement

Treat local spline completion distance separately from the final mission-goal
tolerances. It must be smaller than the shortest intended recovery displacement;
otherwise a recovery can be declared complete without performing the correction.
Validate the actual native tracking command on a recorded error state and an
inside-tolerance state, then verify the generated profile and run the complete
original route. v176/v177 use2cm local capture for a5cm recovery prefix; the old
15cm capture emitted zero at4.9246cm measured endpoint error. Five Linux route
passes establish only the declared original-scenario result. They do not remove
the need to audit post-revocation physical drift or qualify other scenarios.

## 10. Terminal correction failure is not goal completion

Do not copy a mission-goal XY latch into local-curve completion and promote it
without physical validation. v185/v186 passed native component tests but only
achieved3/5 and2/5 original-route arrivals; both failed the declared endpoint
criterion. The unchanged v17706–10 control achieved5/5. These results reject
adoption without establishing exclusive causation for every route failure.

A bounded terminal correction must explicitly distinguish normal completion
from failed tracking. The v187 candidate retains ordinary2cm capture and only
limits nonzero correction below0.1m/s within5cm after curve expiry to1.5s.
Failure goes through exact-owner zero/cancel and PlannerException, followed by
the existing measured-stop/replan protocol. A zero command is not physical
stillness. Reset correction timing for new accepted curves, normal zero,
leaving the terminal region and heading/mission-yaw handling. Do not bypass
collision, PVA, freshness or measured-stop checks to obtain a passing route.

Check both the actual loaded plugin's fault protocol and complete original
routes with actual policy inputs. No-event trials are not evidence that timeout
recovery was physically exercised. Keep failed versions and untouched cohorts.

Before freezing a launcher, verify all required quality-receipt fields,
including `native_packages_available == 14`. v184's missing field correctly
prevented physics despite passing component checks. Preserve that failed
launch and frozen metadata; use a new execution version for corrections.
