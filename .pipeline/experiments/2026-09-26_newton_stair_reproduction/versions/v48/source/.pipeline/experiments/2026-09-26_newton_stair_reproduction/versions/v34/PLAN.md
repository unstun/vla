# v34: SCAN adds PCT's uninflated floor where its navigation ground lacks it, except beside drops

Stage: experiment + analysis. Parent: v33. Native parent: `runtime/scan64_input_refresh_v31` (v31's build, which v32
and v33 ran unchanged).

## Decision and basis

- **Dr Sun, 2026-09-29, after the corridor-entry diagnosis** (`audits/2026-09-29_corridor_entry/RESULT.md`), chose
  "Floor fallback in SCAN". The option as offered was a code change: where PCT's map has no usable floor at a spot,
  SCAN may use the surface map's floor there if it is within 0.12 m of the robot's floor level. It was preferred over
  correcting the pinned map at the two spots, or at the wrong-height cells only.
- **The trial, same day:** a single trial on gpu5070ti, as for v33 (same runner rules, host note, abort rule and
  retry rule).
- **A refinement made in building v34 (reported to Dr Sun; stricter, never looser than the option as offered):** a
  drop guard. Offline, 15,451 of the 39,999 evidence layers the navigation ground lacks lie within 0.35 m of a lower
  level where their own level is absent. A fallback without the guard would therefore let a footprint circle sit at a
  stairwell or opening edge, which PCT's inflation keeps clear today. The guard rejects exactly those (below).

## Motivation

The diagnosis replayed v32's and v33's corridor-entry stands with the native planner and found two blockers in PCT's
pinned navigation ground (`ground_precise.f32`), both turned into planning failures by SCAN's support query:
- **Wrong-height cells (v32):** four corridor cells carry only the landing height, 1.419 m, where the floor is
  1.561 m. Curve samples over cell (47, 41) fail the body-cell height match by about 1 cm.
- **A narrow entry band (v33):**
  - **The band:** the floor band is 0.8–1.0 m wide. In rows 47–53 it ends 0.597–0.697 m short of the body-height
    wall face at x = −4.1983 measured by LiDAR (the revised audit's `entry_geometry.json`), and PCT's
    route runs 0.04–0.17 m inside its east edge.
  - **Why it fails:** SCAN needs both footprint-circle centres over navigation cells with a floor layer. Headings
    within about 45° of east–west are therefore unsupported at the stand.
  - **At v33's start:** the rebound optimizer checks its first control points there at 0° (two coincident points)
    and at −98.96°. All three are unsupported, so SCAN reports "The robot is inside an obstacle".
- **Counterfactual grounds:** fixing the four cells alone unblocks v32's stand, not v33's. Filling the entry band
  unblocks v33's. With both fixes, both stands plan on the first attempt.

The surface evidence (`raw_ground.f32`) is PCT's own uninflated selection of the same ground (traversability cost
≤ 20, computed on the original PCD points plus dense mesh samples, `audits/2026-09-27_dense_static_sampling`). v30
already lets it vouch for the ring PCT's inflation trimmed, in the step score. v34 lets it supply the floor itself
where the navigation ground has none at that level.

## The rule

When SCAN accepts its ground inputs, its copy of the navigation ground gains an evidence floor layer where both
conditions hold:
1. **The navigation ground lacks it.** The navigation cell containing the evidence cell's centre has no layer within
   0.12 m (`body_height_tolerance`) of the evidence layer. This includes layers the rule added earlier in the same
   pass.
2. **No drop lies within 0.35 m** (`double_cylinder_radius`, the footprint circle's radius). Every evidence cell whose
   square comes within 0.35 m of the candidate cell's square is either:
   - **floor:** it has a surface within 0.26 m (the step capability) of the layer; or
   - **solid:** it has no such surface and none below, but a surface above (a wall under an upper floor).

   A cell with a surface more than 0.26 m below the layer and none within 0.26 m of it is a drop. So is a cell with
   no surface at all. One drop rejects the layer.

The added layer is a navigation layer like any other:
- **Height and status:** it takes the evidence height and the decoder's default status (`Stair`) before scoring.
- **Scoring:** the step score (v30's rule, with the same evidence) labels it with the rest.
- **Consumers:** the support query, the decision and every planner step read the augmented ground unchanged.
- **Unchanged:** the navigation ground's own layers are never changed or removed.
- **Unusable evidence** adds nothing: evidence that is absent, invalid, in another frame or at another resolution
  leaves the ground exactly as v33 had it, as v30 treats unusable evidence.

**Offline effect on the pinned grounds** (a Python model of the rule; the contract's oracle is written separately):
- **Added:** 17,214 layers in 15,899 cells: 14,458 on the ground floor (0.06 m), 1,205 on the upper floor (1.5–1.6 m)
  and the rest higher.
- **Rejected by the drop guard:** 22,785 candidate layers.
- **At the entry:** rows 46–53 widen from an east edge at x −4.795 to −4.495. The measured body-height wall face is
  at x −4.1983 in rows 47–53; rows 45–46 open onto the corridor (the revised audit).
- **The four wrong-height cells** gain the 1.561 m floor.
- **The static route screen** (`audits/2026-09-29_corridor_entry/route_support_margin.py`'s method): poses with less
  than ±30° of supported heading fall from 97 to 77.
  - The 15 narrow poses of the entry group (route poses 79–96) all clear.
  - Recomputed after K2 with the layers scan65 actually adds (`route_screen_native.py`, `route_screen_native.json`):
    the same 77, and none in the entry group.
  - The rest are at the corridor's east-end corner and further on, mostly beside drops the guard keeps.

## Exact change

`materialize.py` copies `runtime/scan64_input_refresh_v31` to `runtime/scan65_evidence_floor_v34` and changes three
files. It inserts lines only; it asserts that removing them gives back the scan64 bytes and keeps every line ending.
1. **`plan_env/include/plan_env/evidence_floor_fill.h` (new):** `addGuardedEvidenceFloor(navigation, evidence,
   tolerance, step, guard_radius, summary)`. It is a pure function, the rule above.
2. **`plan_env/include/plan_env/grid_map.h`:**
   - includes the new header;
   - adds the member `reactive_navigation_ground_`, the navigation ground as decoded, kept so that new evidence is
     always applied to the original and never to an augmented copy.
3. **`plan_env/include/plan_env/scan_reactive_grid_methods.inc`:** the two ground callbacks.
   - **The tomogram callback:** keeps the decoded navigation ground, augments it with the current evidence, scores
     the result (v30's rule), and on acceptance stores the augmented ground as the raw ground and its scores as the
     terrain.
   - **The surface callback:** re-augments the kept navigation ground with the new evidence and rescores it, so the
     result does not depend on message order.
   - **A log line** gives the added and rejected counts.

The planner YAML files are v33's copies, unchanged. Every other byte of the native tree is scan64's.

## Preserved

- **Inputs:** the pinned navigation ground and surface evidence bytes, and their publishers.
- **Queries:** the step score and its evidence rule and parameters; the support query and `CollisionDecision::decide`
  (code and thresholds); the body clearance and height tolerance; the known-footprint waiver; the LiDAR occupancy and
  inflation; and the stale, missing, out-of-map and map-boundary verdicts.
- **Planner:** the frontier walk, A*, the optimizer, all manager gates, the FSM and its replan limit; the controller,
  executor and emergency hold.
- **The rest of the stack:** v33's simulation-time pose gate and backstop, the backend, the bridge and the Newton
  worker; PCT's route.

## Acceptance plan and expected signals

1. **K1: materialization and build.**
   - Byte-exact insertion (removing the inserted lines gives back scan64, per file); `changes.patch` applied to
     `parent_source/` reproduces the three files.
   - A build in the pinned image from the scan64 colcon cache, with source identity checked before and after.
   - The recompiled translation units, changed installed files and warnings are listed against scan64.
2. **K2: the red/green fill contract** (`fill_contract/`).
   - **Builds:** one source is compiled against scan64 (red) and scan65 (green).
   - **Header part (green only):** the header does not exist in red. Synthetic cases:

     | Case | Expected (green) |
     |---|---|
     | Band trimmed beside a wall (only higher surfaces beyond) | floor added up to the solid cells |
     | Isolated wrong-height cell inside a floor | floor added; the wrong layer kept |
     | Lower level 0.30 m away (inside the guard) | not added |
     | Lower level just beyond the guard (square distance > 0.35 m) | added |
     | Neighbour with no surface at all inside the guard | not added |
     | Navigation layer within 0.12 m | not added |
     | Navigation layer 0.13 m away | added beside it |
     | Evidence absent, another frame, another resolution, empty or non-finite | nothing added; output equals input |
     | Evidence origin offset by a sub-cell amount | added in the navigation cell containing each evidence centre |
     | Duplicate candidates for one navigation cell | added once |

   - **Real map:** green's added layer set on the pinned grounds equals an independent Python implementation of the
     rule (`fill_contract/oracle.py`) exactly, and the navigation layers are all kept.
   - **Node, both builds:** delivery orders navigation then evidence, evidence then navigation, then malformed
     evidence, then valid evidence again.
     - **Green:** the node's raw ground and terrain must equal the header result for the evidence currently usable,
       and never include layers added for superseded evidence.
     - **Red:** the node's must equal the navigation ground scored as scan64 scores it.
3. **K3: the two frozen corridor-entry stands** (`audits/2026-09-29_corridor_entry/{v32,v33}_stand`).
   - **The probe:** `corridor_probe` rebuilt against scan65, with the pinned grounds.
   - **Expected (green):** both stands' live entry plans on the first attempt, and the committed curve passes the
     native full check.
   - **Red:** the audit's records, which reproduce both live failures.
4. **K4: saved states and native regression.**
   - **Suites:** v31's saved-state suite (`runs/v31_saved_states02`'s inputs) and complete native regression suite
     (`runs/v31_native_regression03`'s inputs), on scan65, with no other container on the Docker VM.
   - **Comparison:** outputs are compared with scan64's recorded outputs. Every difference is explained before
     freezing, not waived.
   - **Differences are expected** where added floor changes support: candidate sets, seeds, attempt sequences and
     accepted curves.
   - **The 8 measured obstacle cases** must keep their verdicts, and the drop and wrong-level negatives must hold.
5. **K5: independent review.** A read-only review of the change, the contract and the evidence.
6. **Freeze, then one physical trial on gpu5070ti** (`PHYSICAL_RUN_PLAN.md`, written before the freeze).
   - **The run:** the historical full route with v33's profile, with `--native-build runtime/scan65_evidence_floor_v34`
     and `--integration-version v34`.
   - **Expected:** no stand at the corridor entry from either blocker.
   - **Not expected to change:** the tight windows at the corridor's east-end corner and further on, which lie beside
     drops the guard keeps.

## Claim boundary and residual risk

- **What support now means.** v34 changes what SCAN treats as supported ground. Where PCT's inflation trimmed floor,
  SCAN's footprint may now stand on it, and walls there are left to SCAN's LiDAR occupancy, as v30 already left
  them for the step score.
- **The drop guard's residual:** it reads only the evidence.
  - A cell with no surface at its level and nothing below, but a surface above, is taken as solid. An opening above
    ground that PCT's uninflated selection also excludes would be taken for a wall; LiDAR does not see voids.
  - The guard covers the footprint circle: evidence cells within 0.35 m of the cell's square. A drop farther away is
    not guarded by v34; there the navigation ground's own layers and PCT's inflation margin are unchanged.
- **The evidence is not bound to the map** beyond frame and resolution (as in v30). In simulation both grounds come
  from one Building; real-robot use would need both from the real map.
- **Ground-floor additions** (14,458 layers) change support before the stairs too. Start and approach behaviour may
  differ from v33's.
- **The added layers are scored like navigation layers.** Next to a wall the step score may leave an added edge layer
  `Unknown`, which blocks as before.
- **Not addressed:**
  - the 0° heading of coincident start control points;
  - the replan start at the executing curve's end;
  - the 1,000-replan limit;
  - the tight corners beyond the corridor entry.
- **Labels.** Only a physical run can support a navigation claim. A version increment is not acceptance, and v3 remains
  the last accepted condition.
