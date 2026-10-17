# Newton contact capacity and geometry-only trials

Scope: the bounded local Newton experiments dated 2026-09-26. These rules do
not declare stair navigation, hardware sensing or physical-robot deployment
validated.

## Physics capacity

The mesh-contact scene uses Newton `SolverMuJoCo` with MuJoCo-Warp on CPU and
Newton's collision pipeline. The earlier flat locomotion trial used native
MuJoCo CPU; do not conflate the solver conditions.

For detailed meshes, use the pinned solver's documented automatic `nconmax`
and `njmax` estimates or a separately verified explicit budget. A small budget
that works on a flat plane is not sufficient evidence for a detailed actor.
`Lite3Newton.step` must reject a generated contact count that exceeds either
the collision buffer or solver capacity before integration. A warning followed
by plausible-looking motion is not valid physics evidence.

Evidence: `flat_static_human_live_v3` exceeded the old 100-contact capacity.
The same-command `flat_auto_capacity_replay_v1` uses the native 1218/4872
estimates, matches the first seven seconds exactly and remains upright through
30.7 seconds. `flat_legacy_capacity_guard_v1` is the expected negative test.
Nine checks are in `validation/flat_contact_capacity_review.json`.

## Contact scoring

Newton contact candidates include the per-shape detection gap. A positive
candidate count is not proof of surface contact or penetration. Use the pinned
`contact_surface_separation` helper and body-frame-to-world transformations
from the actual state. Record the sampling cadence. Remove the detection gap
when estimating physical bounds from native broadphase AABBs, while retaining
real shape margins. Bounds from observed poses are not universal joint-motion
bounds.

## Class-independent navigation

Geometry-only episodes consume measured clouds, synchronized body/sensor
poses, terrain support and the requested route. Do not launch or require a
person tracker for readiness or collision decisions. Simulator obstacle
positions, identities and mesh labels are used only for simulation/scoring.
Simulator body pose remains the localization source and must be labeled so.

Unknown/occupied/out-of-map cells and stale geometric inputs remain blocked.
Footprint initialization may resolve Unknown inside the fresh current robot
footprint, but cannot erase measured or inflated occupancy. Positive terrain
classification must not override current or retained nonterrain hits.

Separate native search success, accepted published B-splines, command execution,
measured stops, surface contact and actual goal completion. Intermediate local
targets must not replace the original goal. Restoring an upstream optimizer
does not remove final endpoint, dynamics or whole-curve collision checks.

## Evidence and unresolved boundaries

The repair report under
`.pipeline/experiments/2026-09-26_newton_stair_reproduction/repairs/2026-09-26_generic_occupancy/`
records exact source revisions, hashes, candidate outcomes and failures.
Flat support data must be generated/read in the pinned PCT NumPy environment;
NumPy 2 pickle module paths are not compatible with this NumPy 1.21.5 runtime.

Sensor freshness watchdogs and total goal wall budgets are different controls.
When CPU execution needs a longer total goal budget, record it explicitly and
keep the physical episode bounded. Do not silently relax sensor/command ages.

Stable static-human passage, box arrival and obstacle-removal clearing remain
open. Human v4 is one actual arrival pilot; v5 did not arrive and box v1 failed
before movement. Candidate versions or successful compilation do not close
these gates. Original Isaac A4 also remains open, and the remote server remains
stopped. Apply the prospective `FLAT_ACCEPTANCE.md` checks, including a read-only
native surface-contact observer before every 1 ms integration step. A 50 Hz
contact trace is weaker evidence and cannot be promoted to full-rate scoring.

## Voxel-boundary regression

Do not interpret a mathematically flat B-spline as having changed floor level
because its evaluated height differs by one floating-point rounding unit.
Capture actual controls/knots and reuse the native complete-curve sampler before
changing geometry or motion limits. Compare raw queries with explicitly labeled
diagnostic controls; do not silently snap the navigation trajectory.

The scoped SCAN index repair adapts Voxblox `c8066b0`'s `floor(scaled + 1e-6)`
coordinate convention to both sensor insertion and queries. The epsilon is in
voxel-index units, not meters. At 5 cm resolution it is 50 nm. Raw captures and
actual occupied/unknown negative controls must remain available. The regression
in `flat_curve_map_native_v1/v2` eliminates six rounding-induced refusals while
preserving two real collisions in an earlier curve.
