# SCAN / EGO-Planner ESDF-free `(p_j, v_j)` Rebound Animation

Created: 2026-10-16. Stage: planning (mechanism explanation). Label: explanatory
illustration only. It is **not** a reproduction, integration, or validation of
SCAN Planner.

## Contents

| Path | Role | SHA-256 |
| --- | --- | --- |
| `scan_pv_rebound_animation.html` | Self-contained film (single canvas, no network) | `5f1e24489ec4f818936bd23543b07ea410fbc2a2041b076832b742d3e618401f` |
| `src/scan_core.js` | 2-D geometry core mirroring the C++ logic | `c431d03a9674c01cb06694b14d205693643ae1fdb663913e809c7f7262d5313f` |
| `src/film.template.html` | Rendering, timeline, captions | `f03e6892ac5a79db4ca2ae98331633b745ff96f162b46d265adc7dcf84b79354` |
| `src/build.js` | Inlines the core into the template | `4f84cf79d113c382dc87ade37ba4807a1683658a19da67ed5a50b50298fbbef1` |
| `src/test_core.js` | Node check: segmentation, A*, `(p, v)`, post-rebound collision | `40b3859681e92b35c814beb3da5e49115fd8389060b02e16eb8d3d2d18d3b90e` |

## Usage

Open `scan_pv_rebound_animation.html` in a browser. Controls: `Space` play or
pause, `←/→` previous or next step, and click the bottom progress bar to seek.
`window.setFilmTime(t)` seeks for frame inspection.

## Regenerate

```bash
cd docs/research/animations/2026-10-16_scan_pv_rebound/src
node test_core.js 1.5   # expect: segments [[2,6]], Q5 steps=6 d=-2.60, curve hits final 0
node build.js           # rewrites ../scan_pv_rebound_animation.html
```

## Source Mapping

Reference implementation (local-only, ignored by `references/upstream/.gitignore`):
`references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_scan_foxy/src/bspline_opt/src/bspline_optimizer.cpp`,
SHA-256 `9744424bd58841213230e95b252706360b1d4db10eaf30e7f6bf34a857a87568`.

| Film step | C++ location | Mirrored behaviour |
| --- | --- | --- |
| 01 Collision segmentation | L72–L130 | Samples the control polygon `Q_{i-1} → Q_i` with step `res / avg_seg / 2`; `in_id = i-1`, `out_id = i` |
| 02 Guide path | L132–L154 | A* from `Q_in` to `Q_out` on the inflated grid (8-connected stand-in for `dyn_a_star`) |
| 03 Normal-plane intersection | L236–L272 | `ctrl_pts_law = Q_{j+1} - Q_{j-1}`; walk from the A* middle vertex by the sign of `(Γ_k - Q_j)·law`; linear interpolation |
| 04 Ray stepping | L277–L294 | From `P_int` toward `Q_j` in steps of one `res`; on the first occupied sample back off one step, which gives `base_point` |
| 05 Direction and distance | L291, L421 | `v_j = normalize(P_int - Q_j)`; `d_j = (Q_j - p_j)·v_j` |
| 07 Rebound cost | L405–L441 | `e = s_f - d`; `e^3` for `0 ≤ e < s_f`, `3 s_f e^2 - 3 s_f^2 e + s_f^3` for `e ≥ s_f`, zero for `e < 0` |

## Simplifications (Claim Boundary)

- 2-D occupancy, `res = 1` cell, one-cell inflation. SCAN's yaw-aware footprint
  check (`getInflateOccupancy(pt, yaw)`) is represented by the inflated grid.
- The optimizer uses only jerk smoothness plus the rebound distance cost
  (`λ_s = 1`, `λ_c = 20`, 600 gradient-descent steps, `s_f = 1.5`). Feasibility
  and fitness terms are omitted.
- The first and last **2** control points are fixed. The C++ code fixes
  `order_ = 3`; with 3 fixed points this toy case still collides after one
  round, and the real planner would call `check_collision_and_rebound()` to add
  new `(p, v)` pairs. That second round is not animated.
- The segmentation scan covers the whole control polygon, whereas the C++ code
  scans `i ∈ [order_, i_end]` (first 2/3 of the points).
