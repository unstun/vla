# Continuous endpoint repair — v253 / v254 native, v255 A02 physics

Final result: the recorded supported A02 start attaches without substitution; the frozen final treatment completes one A02 physical route and terminal PD. Original start/goal, RL, 0.35 m hard support/collision radius and 0.1 s scan period/deadline are unchanged.

## Mechanism and version boundary

- v253 adds two transient continuous endpoint nodes to PCT. Rounded indices select the ordinary one-cell candidate neighbourhood only. They never replace physical start/goal coordinates. Every attachment edge uses actual XYZ, the same planning heading, dense <=0.025 m native support review, legal floor transitions and gap-aware ENV225 cost including both endpoints.
- Native floor association uses actual XY/height. Stored slice aliases remain hints; no scene identity, connected-component exception, endpoint snap or radius change enters the algorithm.
- Both GPMP orders initialize priors from those endpoints and retain exact boundary positions before GP interpolation. The original dense height projection and full static/SCAN validators retain admission authority.
- v254 restores floating-point legacy diagonal edge distance and adds an accumulated-score regression. It changes no configured physical-mode route: all 55 admitted route CSVs match v253 byte for byte.
- v255 is execution/configuration binding only: frozen v254 installation, frozen v248 bridge and original v241/v237 physics/scanner chain. Only A02 is launched in this follow-up. G07/R11 retain their earlier v252 physical controls; they are not new v254 physical runs.

## Offline qualification

- Recorded v252 A02 request: first GPMP and complete static review pass; start and goal XYZ errors are both exactly 0. The replay is global/static only; nominal scan fixtures are not claimed to recreate the live measured-body/cloud state.
- H00 original-route control passes first GPMP, full static review and cold SCAN publication, with zero goal coordinate error.
- Unchanged 12 x 5 matrix: 55/60 first-GPMP and full native/static/cold-local passes. All 55 admissions avoid graph fallback. B09 remains 0/5 and remains in the denominator.
- Seven PCT targets / 48 cases, 97 native regression cases and 10,855 support parity queries pass. Typed and exported native admission mismatches are both 0. Test suites overlap in the environmental-cost target; these are suite counts, not claimed unique independent cases.
- Source, 392 installed files, unchanged fixtures, evaluator binaries and policy hash are frozen before scoring. See the version manifests and acceptance receipts.

| Case | First GPMP / 5 | Full component pass / 5 | Min ENV extra edge (m) | Min raw-solid reference (m) | Median global (s) | Median cold local (ms) |
|---|---:|---:|---:|---:|---:|---:|
| A01 | 5 | 5 | 0.1407 | 0.0990 | 0.643 | 28.73 |
| A02 | 5 | 5 | 0.0727 | 0.0990 | 0.639 | 18.24 |
| A03 | 5 | 5 | 0.1389 | 0.0990 | 0.542 | 28.85 |
| A04 | 5 | 5 | 0.1440 | 0.0990 | 0.570 | 29.78 |
| G05 | 5 | 5 | 0.0200 | 0.0990 | 0.727 | 68.75 |
| G06 | 5 | 5 | 0.1400 | 0.0990 | 0.680 | 11.81 |
| G07 | 5 | 5 | 0.1399 | 0.0990 | 0.843 | 9.48 |
| B08 | 5 | 5 | 0.0765 | -0.1869 | 0.825 | 9.32 |
| B09 | 0 | 0 | N/A | N/A | 0.483 | N/A |
| R10 | 5 | 5 | 0.1412 | 0.0990 | 0.774 | 27.71 |
| R11 | 5 | 5 | 0.1423 | 0.0990 | 0.887 | 26.31 |
| R12 | 5 | 5 | 0.1426 | 0.0990 | 1.032 | 44.95 |

B08 retains a negative independent raw-solid reference margin (-0.1869 m). Its component admission is not a full-route body-clearance proof. ENV values are capped soft-field margins, not per-foot landing clearance. The global durations include installed plugin and static admission work; they are not standalone optimizer timings.

## Single A02 physical result

| Metric | Measured result |
|---|---:|
| Formal attempts / completed route | 1 / 1 |
| Terminal state / recording end | FINISHED / 112.589752 s |
| First arrived observation | 110.550873 s |
| Final XY / height / yaw error | 0.108795 m / 0.006334 m / 0.047409 rad |
| Measured final PD suffix | 4.397583 s |
| Navigation local success | 2474/2494 (99.1981%) |
| Cross-floor local success | 2144/2162 (99.1674%) |
| Full cross-floor window | 21.000088–98.897278 s |
| Cross-floor pauses >=0.5 s / >=1 s | 0 / 0 |
| Cross-floor native body support | 780/780 Free |
| Cross-floor min ENV extra edge | 0.091264 m |
| Whole-navigation native body support | 984/984 Free |
| Whole-navigation min ENV extra edge | 0.007278 m (initial low-margin start) |
| Whole-navigation min raw-solid reference | 0.086453 m |
| Emergency publications | 0 |
| LiDAR complete / deadline failures | 1016 / 0 |
| Maximum scan time / unchanged period | 31.726624 ms / 100 ms |

Whole-navigation pause counts include two genuine low-speed intervals: initial planning wait (12.2013–16.0628 s, 3.8615 s) and terminal settling (105.9734–110.5509 s, 4.5775 s). They are not excluded to claim a zero-pause whole route. The cross-floor interval has no long pause or active-curve gap. The raw 109–115 s window is incompletely recorded and is not treated as a full-window zero.

Successful local planning frequency is 24.355 Hz; maximum solve is 426.160 ms. Sustained 30 Hz remains unvalidated. There is no fall/process failure; the original finish_request closes FINISHED. This is one physical regression, not a reliability or new-map/slopes/foot-coverage claim.

## Source and delivery proof

- Final source/install/fixture/evaluator/bridge gate passes after execution. Actual loaded planner/controller library hashes match the frozen v254 inventory.
- Original A02 scenario and numerical/profile gate pass; original RL golden parity and 0.35 m / 0.1 s settings are preserved.
- Full video is 1280x720 at 30 fps, 3371 frames. All first/last source states are included; every rendered causal index is checked and no future curve is shown. Local full decode and SHA verification pass.
- `delivered/v255_A02_full_attempt01.mp4` is the full physical recording. `delivered/v252_vs_v255_A02_side_by_side.mp4` compares it to the old failed A02 prefix. The old side explicitly holds its final failed frame after the prefix ends; no additional physics is generated.
- 287 hash-listed compact proof/media files are returned locally. Heavy raw capture (290,496,224 bytes, SHA 7b1af5c7a67131a25c14ba1b242c6b262b578eb0e293801a252b414e831e7bc9), dense route exports and build artifacts remain remote with provenance.
- Six full-video sample frames and one comparison frame are visually inspected, with original clocks and version labels visible.

## Preserved development records

Frozen v251 fails all three initial public endpoint tests. v253 preserves the initial 46-case build receipt and a complete 47-case rerun: copy2 preserved an older source mtime and retained one stale test object. The final v254 fresh build runs all 48 cases, including the legacy-distance regression. Frozen predecessors are not rewritten. The local comparison tool first found ffmpeg lacks drawtext; the corrected display-only adapter uses a deterministic PNG title overlay. Neither display operation starts physics.

Only old CMake object/dependency intermediates are reclaimed (1,111,989,146 bytes); installed libraries, test executables, logs/XML, models, raw evidence and videos are retained. No commit, task archival or baseline promotion is performed. Selected physical baseline remains v232/v233.

Primary evidence: [offline qualification](../../versions/v254/results/acceptance_receipt.json), [matrix](offline/v254/matrix_table.csv), [full-route gate](physical/A02/results/full_route_verification.json), [window metrics](physical/A02/results/window_audit.json), [local quality](results/local_quality.json), [return manifest](return_manifest.json).
