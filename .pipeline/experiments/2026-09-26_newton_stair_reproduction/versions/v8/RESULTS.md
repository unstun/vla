# v8 results

Stage: experiment + analysis.

The original v7 sparse-neighbor test fails; v8 passes the same test and existing
geometry/unknown/stale/current-and-historical-obstacle negatives. Native build
passes with unchanged frozen source.

Two original 66-scan native replays agree exactly. The admitted reference
frontier expands from 0.3479057 to 0.4473073 seconds (about 9.94 cm beyond
the previous endpoint), but target selection and continuation still reject a
nonterrain-inflated point under the body-to-target heading. No physical route
was launched and v8 is not a navigation pass.

See `runs/v8_native_continuation01/` and `audits/2026-09-27_v8_geometry_ablation/`
for the separate old-envelope diagnostic. Production source remains frozen.
