# SCAN Planner Step 4 (`STEP 3: REFINE(RE-ALLOCATE TIME) IF NECESSARY`) Animation

- **Single-File HTML**: [`scan_time_refine_animation.html`](./scan_time_refine_animation.html)
- **SHA-256**: `340897fbea0a3365f30e04d2f2f17f3aa992e5a13893b13679420d49cb41e20d`
- **Build Command**: `node docs/research/animations/2026-10-16_scan_time_refine/src/build.js`
- **Test Command**: `node docs/research/animations/2026-10-16_scan_time_refine/src/test_core.js`

## Source Code Mapping (`pct_scan_foxy`)

| Act / Step | Time Window | C++ Function | Upstream File & Lines |
| :--- | :--- | :--- | :--- |
| **Step 01** | `3.5s – 13.5s` | `checkFeasibility(ratio, false)` | `src/bspline_opt/src/uniform_bspline.cpp` L134–L192 |
| **Step 02** | `13.5s – 26.5s` | `lengthenTime(ratio)` | `src/bspline_opt/src/uniform_bspline.cpp` L194–L205 |
| **Step 03** | `26.5s – 38.5s` | `reparamBspline(..., dt1)` | `src/plan_manage/src/planner_manager.cpp` L489–L508 |
| **Step 04** | `38.5s – 49.5s` | `parameterizeToBspline(ts, point_set, start_end_derivative, ctrl_pts)` | `src/bspline_opt/src/uniform_bspline.cpp` L209–L279 |
| **Step 05** | `49.5s – 62.5s` | `calcFitnessCost(g_q, cost, gradient)` | `src/bspline_opt/src/bspline_optimizer.cpp` L951–L962, L1173–L1199 |
| **Step 06** | `62.5s – 74.5s` | `BsplineOptimizeTrajRefine(...)` (`COST_PHASE`) | `src/bspline_opt/src/bspline_optimizer.cpp` L443–L471 |
| **Step 07** | `74.5s – 86.0s` | `checkDynamicFeasibility()` | `src/plan_manage/src/planner_manager.cpp` L402–L441 |

## Architecture (`One HTML, One Canvas, One draw(t)`)

- [`src/refine_core.js`](./src/refine_core.js): Pure mathematical core implementing cubic uniform & non-uniform De Boor evaluation, derivative control points $V_i, A_i$, `checkFeasibility`, `lengthenTime` (boundary span freezing `i <= num1 = 5`, `i > num2 = 9`), uniform sampling + `(K+4)x(K+2)` linear solver `parameterizeToBspline`, anisotropic 5:1 tangent-normal ellipse `calcFitnessCost` ($a^2=25, b^2=1$), and `BsplineOptimizeTrajRefine` L-BFGS optimization.
- [`src/film.template.html`](./src/film.template.html): Single-canvas 60fps renderer with 3 synchronized viewports (2D Trajectory & Control Polygon + Macro Zoom on 5:1 Anisotropic Ellipse, Knot Vector Timeline Track $u_0 \dots u_{14}$, and Axis-Wise Kinematic Profile $|v_d(t)|, |a_d(t)|$).
