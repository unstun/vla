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
the parent difference in `changes.patch`. Earlier physical runs and their
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
