# Local Newton navigation versions

Dr Sun designated the delivered empty-floor system as v3 on 2026-09-27 and requested one version per change. These version numbers describe this local simulation integration, separately from native SCAN candidate/build numbers.

| Version | One change | Evidence status |
|---|---|---|
| v3 | Registered current empty 12 m PD/RL baseline | One bounded trial validated; not generally stable |
| v4 | Connect the same control chain to the complete archived Building | Factory/PD pass; navigation fails before motion. See [result](v4/RESULTS.md) |
| v5 | Restore explicitly selected height optimization | Frozen failure repaired; Building starts moving but continuation fails; new empty-floor trial also fails. See [result](v5/RESULTS.md) |
| v6 | Admit map-resolution-sized local continuations through shared native guards | Captured 17.4 cm continuation passes and executes; full Building remains unsuccessful. See [result](v6/RESULTS.md) |

Current integration: **v6**. Last accepted navigation condition: **v3, empty
12 m floor only**. Videos are ordinary files under
`output/2026-09-27_lite3_versions/`: `v3_empty_12m.mp4` and
`v4_building_test.mp4`, `v5_building_test.mp4`, `v5_empty_test.mp4`, and
`v6_building_test.mp4`.
A failed new version never replaces the older outcome.

Before editing a new logical behavior or configuration, create the next integer version and state its scope. Preserve a hash-verified source snapshot and exact difference from the parent before running it. Keep immutable run IDs under runs/ and associate every attempt, including failures, with its version. Keep results separately from the frozen source manifest. A new version does not mean a successful version. Record the last validated condition explicitly. Do not put a release tag on unrelated dirty repository changes. Earlier v1/v2 are not reconstructed or relabeled. No automatic pre-edit commit is performed.
