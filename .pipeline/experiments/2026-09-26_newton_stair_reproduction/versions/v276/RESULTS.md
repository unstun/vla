# v276 Independent raw-point material reconciliation

Frozen manifest: `b6a0bc474a855e15943d8ab17272fc574893540569b50c17389189ed9044c3be`.
This is a derived audit of saved v273 trajectories, not a new planning run.
All 172 input tables are SHA-bound and unchanged. Original scores and v275
partial correction remain in the adjacent audit directory.

## Mechanism and controls

Nearly vertical staircase faces amplify sub-micrometre float32 source/point
registration differences into centimetres when height is inferred from XY.
Use bounded three-dimensional correspondence only to establish material identity,
then test membership below a finite clipped upward source cap. Original raw XYZ
coordinates are retained in every distance query. The source-match error bound
is derived from float32 affine arithmetic; incompatible or ambiguous normals do
not grant a material exclusion. No hard collision/support threshold changes.

18 controls, 5,000 generated float32 precision cases and 14 fixed witnesses pass.
The maximum generated point distance / arithmetic bound is 0.091131. B08 remains
exactly -0.13330188244781216 m and rejected. Wall, lateral seam, unknown-normal,
strict critical-step and above-step counterexamples remain refused.

## Complete saved-trajectory result

| Frozen cohort | Original score | Derived full-chain pass | First GPMP | Global median | Minimum independent raw margin |
|---|---:|---:|---:|---:|---:|
| Original 52 (49 positive + 3 illegal) | 8/49 | 38/49 | 38/38 admitted | 2.536750 s | 0.007015842 m |
| Fixed 50 + 3 illegal | 11/50 | 48/50 | 43/48 admitted | 2.743627 s | 0.000986757 m |

All 86 admitted global/local curve pairs have nonnegative independent raw
margins. Both cohorts retain 3/3 correct illegal rejections. These derived
passes apply the unchanged native gates and exact endpoint identity checks;
only the independent material-audit result changes. Frozen v272 source model,
old voxel model, original endpoints, RL, 0.35 m threshold and 0.1 s scans remain.

The physical gate is still FAILED: fixed50 first GPMP 43/48 = 89.5833% is below
90%, and median 2.743627 s exceeds 1.5 s. No new physical attempts or videos.
89 compact returned files for each of v275/v276 and all 17 v276 frozen files
were locally SHA-verified. Large sample tables remain remotely hash-pinned.

See `../../audits/2026-10-19_v273_source_surface_matrix/material_audits/v276/derived_summary.json`
for every route, and `return_inventory.json` for storage and hashes.
