# v30: surface evidence decides walkway-edge drops in the step score

Stage: experiment + analysis. Parent: v29. One rule in SCAN's ETH-style step
score, plus the wiring that gives the rule its input. Dr Sun chose option 1 on
2026-09-28, after the landing-stall diagnosis.

## Motivation

`v29_historical_full01` stopped on the upper landing, and
`audits/2026-09-28_v29_landing_stall/RESULT.md` traces why from saved inputs:

- The pinned PCT navigation ground selects the landing walkway as a band 6–7
  cells (0.6–0.7 m) wide, narrower than the floor.
- The step score marks a layer Unknown when a present 3 × 3 neighbour has no
  layer within 0.26 m. The cells beyond the band exist only for other floors,
  so the band's outer ring is Unknown support.
- The PCT route runs on that ring. From t = 8.695 s, 52 route samples fail the
  support query, and the frontier cannot pass 8.6446 s.
- A probe-only relabel of the 39 Unknown walkway layers in the landing box
  moves the frontier to 11.04 s. The native continuation then plans a moving
  prefix, and the negatives still hold.

## Exact change

`materialize.py` copies `runtime/scan61_sensor_column_v29` to
`runtime/scan62_support_evidence_v30` and changes two files.

1. **`plan_env/eth_step_score_adaptation.h`:** `precomputeEthStyleStepScores`
   takes an optional evidence snapshot. The rule applies when a present
   navigation neighbour has no unambiguous layer within the step capability
   (0.26 m):
   - It is still a possible drop, so the layer stays Unknown, unless the
     evidence cell under the neighbour's centre has an unambiguous surface
     within 0.26 m.
   - If the evidence has one, the neighbour is measured ground, as ETH treats
     a measured cell. Pass 1 includes the evidence height, and pass 2 skips
     it because it has no score.
   - Only navigation cells are scored. Evidence never adds a supported cell.
   - Evidence that is absent, in another frame or at another resolution
     scores exactly as v29 did.
2. **`plan_env/scan_reactive_grid_methods.inc`:** the tomogram callback
   passes the current surface evidence (`/pct_ground_surface`) to the step
   score. The surface callback rescores the accepted navigation ground, so the
   result does not depend on which message arrives first.

Every other v29 byte is unchanged, and the planner YAML files are copied
unchanged.

The version uses the ETH-faithful form of option 1, in which evidence heights
count in pass 1. Offline it differs from the simpler form, which skips the
neighbour, on 1 of 86,775 layers: that layer is Stair instead of Flat. The
faithful form is never less conservative.

## Preserved

- **Inputs:** the PCT navigation selection, which is the only set of scored
  cells, and the surface evidence bytes and classification rule.
- **Step score:** its parameters (0.26 m capability, 0.15 m radii, four
  critical cells and the 0.04 m stair label), the absent-neighbour skip, and
  the drop rule wherever the evidence also lacks the level.
- **Queries:** the footprint support query, body clearance and height
  tolerance; occupancy, the known-footprint waiver, and stale, out-of-map and
  map-boundary verdicts.
- **Planner:** the frontier walk, optimizer, A* and all manager gates; the
  controller, executor and emergency hold.

## Acceptance plan and expected signals

1. **Build** in the pinned image with the scan61 incremental cache. Source
   identity is checked before and after.
2. **Red/green support contract** (`support_contract/`). One source is
   compiled against v29 (red) and v30 (green).
   - **Synthetic cases:**

     | Case | Red (v29) | Green (v30) |
     |---|---|---|
     | Artifact edge: neighbours only on other floors, evidence floor at the level | Unknown | Flat |
     | Real drop: no evidence surface at the level | Unknown | Unknown |
     | Evidence step 0.20 m up | Unknown | Stair |
     | Evidence +0.20 m next to a navigation cell −0.10 m | Unknown | Unsupported |
     | Ambiguous evidence | Unknown | Unknown |
     | Evidence only beyond 0.26 m | Unknown | Unknown |
     | Absent neighbours | unchanged | unchanged |

     With no evidence, evidence in another frame, evidence at another
     resolution or empty evidence, green must equal red on every case. The
     scored cell set must equal the navigation set.
   - **Real map:** with the pinned navigation ground and surface evidence,
     green's labels must equal an independent Python implementation of the
     rule on every layer. Red's labels must equal the validated v29 replica.
     The expected change is 7,513 layers to Flat and 360 to Stair, including
     all 39 landing-box layers.
   - **Node delivery order:** probes built against each install check the
     order evidence then navigation, navigation then evidence, then malformed
     evidence, then valid evidence again. v30's node labels must always equal
     the header result for the evidence currently usable. v29's must never use
     evidence.
3. **Frozen landing and onset states** from the diagnosis audit, with
   `gen_probe` rebuilt against v30 (`plan_env` is static). The frontier must
   pass 8.6446 s, and the continuation must be accepted with the boundary and
   full-curve gates and the negatives, with no oracle.
4. **The seven saved walking-start states:** all must still continue with full
   gates and negatives.
5. **The complete v29 native regression suite on v30:**
   - all continuation replays accepted with full gates and negatives;
   - repeats identical;
   - every output compared with v29.

   Every difference is explained before freezing, not waived.
6. **Independent review:** a read-only review of the change, the contract and
   the evidence.
7. **Freeze, then one physical trial:** the historical full route with
   `v29_historical_full01`'s profile.

## Claim boundary and residual risk

v30 changes what SCAN treats as supported ground. Offline, 7,873 of 86,775
navigation layers (9 %) move from Unknown to Flat or Stair across the
Building. These cells were already in PCT's selection, and each now borders
evidence ground at its level rather than a possible drop. The robot may plan
footprint centres on them. Obstacles there are still decided by LiDAR
occupancy, not by support.

The rule trusts the pinned surface evidence, a dense sampling of the same
static Building mesh. That creates two residual risks:
- **A missing drop:** an evidence surface within 0.26 m of the walkway that
  is not ground the robot can stand on, such as a table or box top beside it,
  would stop an edge from counting as a drop.
- **A mismatch:** evidence that disagrees with the real geometry would do the
  same.

In simulation, both sources come from one mesh. Real-robot use would need
evidence from the real map.

v30 does not address:
- the wall-clock freshness chain (`odom_stale`);
- the emergency-hold feedback;
- the pending 13 cm protrusion choice;
- the Mid-360 blind-zone residual risk that v29 carries.

### Risks widened after the independent review, before freezing (2026-09-28)

The first independent review (`runs/v30_native_regression01/independent_review.json`)
found no code defect, but found the statement above incomplete. The text above
is kept as first written; these points extend and correct it.

- **No drop left to test on this map.** Under v30 the pinned Building has no
  Unknown or Unsupported navigation layer (79,745 Flat and 7,030 Stair; v29
  had 7,873 Unknown). Flat and Stair lead to the same collision decision, so
  in simulation the step score no longer constrains any navigation layer.
  - **What the trial can show:** the physical trial cannot exercise drop
    handling. On this map, walkway edges are kept only by PCT's selection
    margin (its obstacle-distance inflation) and by LiDAR occupancy.
  - **Where drops are still tested:** only offline. These are the synthetic
    `real_drop` case, and the node checkpoint that removes the evidence beside
    the landing ring, after which 10 landing layers are Unknown again
    (`support_contract/`).
- **The evidence is not bound to the map.** Nothing at runtime checks that
  the evidence and the navigation ground describe the same map beyond frame
  and resolution. Any valid evidence snapshot in the frame is trusted.
- **Evidence provenance, corrected.** "A dense sampling of the same static
  Building mesh" understates it.
  - **What it is:** PCT's own uninflated raw-cost ground selection
    (traversability cost ≤ 20). It was computed on 2M original PCD points
    plus 8M area-weighted mesh samples
    (`audits/2026-09-27_dense_static_sampling`).
  - **How it differs:** it differs from the navigation ground mainly by PCT's
    obstacle-distance inflation. In effect, v30 lets the uninflated selection
    vouch for the ring that the inflation trimmed.
- **Planner paths change.** New support changes A* candidate sets, seeds and
  optimizer attempt sequences.
  - **What changed:** apart from the regression's explained `v26` output,
    no committed start-state or regression result changed. Landing and onset
    change by design. The path to these results did change
    (`runs/v30_saved_states01/difference_explanations.json`,
    `runs/v30_native_regression01/log_difference_explanations.json`).
    - At `z_0p3650` v30 adds a failed attempt on the full 3.85 s window, then
      accepts a different spline to the same 1.925 s prefix target (cost
      0.510 → 0.564).
    - At `v23` an extra full-target curve is stopped only by the final
      full-curve gate.
    - At `v18` each of the six failed rebound A* searches now takes
      0.107–0.109 s.
    - At `z_0p3700` v30's full-window search ends on the 0.2 s wall-time
      budget; v29's exhausted its search in 0.188 s. The outcome there
      depends on machine speed.
  - **What is untested:** live replan latency and failure counters under
    these changes, until the trial.
- **Rescoring cost.** The surface callback rescores all 86,775 layers on the
  single-threaded executor.
  - **Measured cost:** one full-map scoring takes 71.8 ms with evidence and
    64.2 ms without (best of 3, pinned image on this Mac's Docker VM,
    `support_contract/green_v30/step.json`).
  - **Exposure:** the evidence publisher sends once (transient local) and
    re-arms only after a simulation-clock reset, so the cost is paid at
    startup. A republish during a run would stall the 50 ms timers for about
    that long.

Only a physical run can support a navigation claim. v3 remains the last
accepted condition until one passes.
