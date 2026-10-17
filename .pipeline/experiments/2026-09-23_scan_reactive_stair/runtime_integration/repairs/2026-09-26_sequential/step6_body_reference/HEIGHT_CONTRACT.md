# Spawn height and locomotion reference height

The fixed V12 source declares **0.35 m for initial root placement** and
**0.30 m for the root-height reward target**. These are separate values. The
previous VLA launcher reused the initial placement value as the PCT, SCAN and
backend height reference. A fresh read of the actual execution copy matches
all three local immutable source hashes; see `height_contract_evidence.json`.
The registry is `Wave-C-Stairs-V12-Lite3-v0`, source commit reported by the
runtime is `8c3fdffa84b85be0704a10ea5b2533817d543822`, and checkpoint SHA-256 is
`a9d31dce90e6e8c564d955e473d6d3502f893d7ef5a5c1efaf5bb50d6b3d5450`.

The pinned reward computes root height relative to estimated ground. Independent
standing evidence over 5–9 s (200 samples) has median 0.296544 m above the
pinned local ground. This supports the source interpretation; the value was
not fitted to make planning pass. It is not a guarantee of exact body height
during locomotion and does not certify collision-free motion.

The new opt-in `--locomotion-height-contract` package preserves physical spawn,
initial geometry and the policy while changing the reference consumers:

| Consumer | Explicit value |
|---|---:|
| Runner spawn and initial AABB | 0.35 m |
| SCAN expected root-above-ground reference | 0.30 m |
| Native PCT optimizer reference | 0.30 m |
| Backend measured-body to ground-start conversion | 0.30 m |
| Backend global goal body-height target | 0.30 m |
| Runner goal-height error metric | 0.30 m |

The old `pilot.nominal_body_height_m` remains 0.35 for compatibility; new
`spawn_body_height_m` and `locomotion_reference_height_m` fields are explicit.
Runtime startup asserts the actual registry reward target and initial root
position before changing the scene spawn. It checks source hashes and records
both values. SCAN's route offset remains zero; height tolerance, inflation,
Unknown blocking and all dynamic limits remain unchanged. Do not change the
legacy field alone, because that would also change actual birth placement.

Three dedicated tests plus six launcher tests pass. Independent review of
`walk_scan24_height030_right_v1` confirmed all package hashes, four consumers,
unchanged spawn geometry, runtime checks and shell expansion. The package is
prepared only until separate execution evidence exists.

`regenerate_pct_inputs.py` runs the actual native PCT at both heights from the
same measured body pose and unchanged ground goal. Attempt v1 failed at import
because the staged adapter lacked its navigation-service dependency; this is
retained. Attempt v2 includes that dependency and completed in the pinned
Humble image with matching returned hashes. Both outputs have 37 waypoints.
The first native body-reference height is 0.408044 m at reference .35, versus
0.358044 m at reference .30, close to the measured start at 0.354542 m.
The old path was not translated to fabricate a new native result.

Paired SCAN CPU replays use these regenerated routes with identical recorded
clouds, body states and tracking messages. Their outcomes, final-spline coverage
and subsequent live behavior must be reported independently of this contract
repair. No navigation-success conclusion follows from source/config consistency.

The paired native runs are now complete; see `PAIRED_RESULT.json`. The 0.35 m
control has 180 seed-search failures and no checked seed or spline. The 0.30 m
reference has no seed-search failures, but 179 seed-edge rejections and no
checked seed or spline. Neither run hits the search time cap. Callback counts
are not a timing comparison. The first corrected run rejects edge 74 at sample
0 after the manager replaces the grid endpoint with the exact local goal.
This motivates endpoint diagnostics; the existing log does not record path
size or the original edge and therefore does not yet prove that edge 74 is
the mutated last edge.
