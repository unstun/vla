# Local Newton reproduction of the archived stair integration

2026-09-26; stage: experiment + analysis. Dr Sun requested reproduction of the
previous work immediately after selecting Newton and reviewing the local
Lite3 flat-ground video. Work remains in the existing in-progress task.
Implementation/checks are inline in the main session.

## Boundary and evidence

Restore the archived Building stair geometry, Lite3 sensor rig, right-side
official animated human, measured point-cloud/current-track input, native PCT
route and SCAN planning/controller loop on this Mac. The last Isaac live trial
had no moving curve. Reproducing its setup does not assert that navigation was
previously successful or that Newton will solve the unresolved planner failure.
Keep unknown/out-of-map blocked and all frozen planner thresholds. Human truth
is for scene animation and separate scoring only; tracks must use ray returns.
No prediction, hidden sensor proxy, kinematic robot trajectory replay, training,
physical actuation or remote reconnection.

Owned new directory:
`.pipeline/experiments/2026-09-26_newton_stair_reproduction/`.
Reuse the qualified Newton virtual environment read-only except for its local
kernel cache. Keep its accepted flat runs immutable. Expected new modules are
source/asset identity and local build orchestration, Newton scene/rig/animation
and ray sensor, transport to the original ROS components, scenario runners,
contract tests and collected evidence. Change an existing Newton adapter only
if an actual reusable scene/initial-state seam is needed, with its original
flat condition regression-tested. Task metadata and focused learned specs may
be updated; preserve unrelated dirty paths and the frozen Isaac archive.

## Conditions to pin before execution

- Exact archived `walk_scan28_height030_right_v1` Building/route/Livox/official
  human/rig bytes; verify file hashes and existing provenance.
- Original `scan_33` source93-file manifest and original planner configuration;
  copy into a new local build tree. Do not modify scan33 or its old build result.
- Cached local ROS Humble image
  `sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb`,
  Linux amd64 under Docker Desktop on M5. It already contains ROS, PCL and OpenCV.
  This differs from the old pinned Foxy image. Record compiler/ABI/dependency
  versions and any necessary compatibility-only source changes. Reuse the
  pinned Linux-amd64 PCT runtime only after an actual import/execution check.
- Newton1.6.0 and its frozen CPU environment from the preceding experiment.
  Physics is MuJoCo through Newton; sensing is geometric ray casting, not RTX.
  Use the original Livox ray table and sensor transforms where supported.

## Ordered gates

1. Source/asset inventory, model/animation parsing and local native SCAN build.
   Build/container setup: up to1200wall seconds per attempt, at most3 compiler
   workers, 6GiB container memory, no remote host. Record and retain failures.
2. Replay original negative and positive recorded inputs with the compiled
   native planner. Distinguish algorithm/source parity from cross-platform
   timing. Do not relax the planner's search/acceptance bounds to get a pass.
3. Verify original Building triangle geometry, dynamic official skin vertices,
   sensor-mount transforms, per-window rays and hits. Animation controls must
   separate rigid root motion from limb deformation. No human truth feed to ROS.
4. Check the rig's physical stance and sensor-only operation before connecting
   closed-loop motion. Preserve actual contact/height/tilt and all returns.
5. Run one bounded closed loop using native current tracks, native PCT/SCAN and
   actual applied locomotion commands. Up to35simulation seconds and900wall
   seconds, then measured stop. Capture raw cloud/state/planner events and video.
   On failure, classify and fix only the evidenced seam; keep every attempt.
6. Decode and visually inspect video; verify clocks, sensor-track provenance,
   received curves, physical progress, contact/fall and stop outcomes. Report
   `integrated`/`validated` only for the tested condition. Isaac A4 remains a
   separate acceptance condition unless explicitly amended and reviewed.

Every execution has an owned process/container name, a deadline and cleanup.
Keep at least10GiB host free; no Docker prune or deletion of existing assets.
Platform integration is reviewable independently from a successful stair route.

## Geometry backend decision

Pinned Newton documentation `docs/solvers/mujoco.rst` states that native
MuJoCo convex-hulls nonconvex meshes. The Building is one concave mesh, so
the previous flat-ground native-contact mode cannot preserve its free space.
Use MuJoCo-Warp on CPU with `use_mujoco_contacts=False` and Newton's own
`CollisionPipeline`; pass contacts into every dynamics step. This preserves
the original triangle surface rather than changing the building to a hull or
heightfield. Qualify this new physics condition before motion. The official
human remains visual/sensor geometry as in the archived run, whose physical
human contact was never validated; report geometric proximity separately.

The first geometric sensor probe retained only2/20000 returns because19998
rays hit the rig's optical cover inside the0.1m valid range. Match the exact
`mid360-optical-runtime.stl` mesh at its URDF scale and treat only this cover
as transmissive in a separate ray BVH; keep its physical/rendered representation,
all other robot returns and all external obstacles. This is an explicit Newton
geometric-material approximation, not proven RTX parity. `nearRangeM` and
`rangeOffsetM` have different meanings in NVIDIA's primary documentation; do
not bypass the entire near range or claim that minimum-range filtering alone
justifies ignoring all occluders. Preserve the opaque-cover failed probes.

Follow-up diagnostics disproved the optical-only explanation: the19998 hits
are shape40 (metal housing), while the exact optical STL is shape41. In the
archived URDF, the scan origin is25.9171mm above the sensor-body origin; the
optical mesh begins at39.3971mm, and the metal mesh reaches39.4991mm. The initial
Newton sensor world pose matches the archived Isaac pose. Therefore keep the
original scan frame and explicitly exclude only both hashed MID360 CAD meshes
from that emitter's ray BVH. Do not move the mount or hide the rest of the robot.
This replaces the ineffective optical-only hypothesis and remains a declared
simulator adaptation, with no hardware or RTX-equivalence claim.

## Upstream-first correction from Dr Sun

Dr Sun subsequently instructed that encountered problems must first be checked
against GitHub open-source implementations rather than resolved by inventing
new workarounds. The optical/emitter exclusions above are retained only as
diagnostic hypotheses and preserved run evidence. The default exclusion is
disabled pending source inspection and an explicit, source-backed sensor
contract. Neither an improved point count nor a passing diagnostic alone
authorizes promotion to the closed-loop condition. Inspect implementations,
pin commits, record applicability and test preserved external occlusion and
robot-body visibility before selecting any upstream pattern.

The follow-up comparison is now recorded in
`.pipeline/survey/2026-09-26_newton_lidar_bridge_upstream_survey.md`. The explicit
sensor mode follows the Robotec/MuJoCo sensor-owner exclusion convention,
resolving the two original URDF link visuals rather than the collapsed body.
`lidar_upstream_contract_v2` passes native-MuJoCo analytic comparison at1.9m,
0.35m and0.06m, unchanged physical/render flags, retained other-robot near
occlusion, and fixed-root/identical-frame official skin controls. This qualifies
only that geometric sensor condition. All failed hypotheses remain preserved.

At the preceding component checkpoint, cross-OS clock handling was the next
unimplemented integration seam. The old
TCP command state compares source and receiver monotonic timestamps; the
applied-evidence reader does the same. Read-only clock probes confirm that this
Mac and the Linux VM have different origins, while sampled Linux parent/child
processes agree within the same progression. Do not infer a reusable constant
offset from a boot-specific probe. MAVROS time synchronization is surveyed,
not integrated; inspect/adopt a supported upstream solution before this seam.
No new HTTP sensor protocol, guessed offset or watchdog relaxation is approved
as a shortcut. Native recorded-input replay remains distinct from a live loop.

The subsequent qualified adaptation is documented in `CLOCK_BRIDGE_PLAN.md`.
The local native loop now runs with actual Newton dynamics/current sensing;
`stair_native_walk_v2` emits two moving curves but fails navigation on unchanged
command timeout after limited motion. Its28s verified video and full-rate
evidence establish bounded integration, not completed stair/person acceptance.
Next: source-backed trajectory retiming diagnosis. Remote Isaac remains stopped.
