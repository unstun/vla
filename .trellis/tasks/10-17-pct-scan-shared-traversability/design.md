# v221 design

Use ../10-17-pct-scan-traversability/design.md as the shared contract. This child introduces the single-source native checker, PCT admission/repair and profile binding. Local failed-round spatial memory remains absent.

The implementation source is a new immutable-version overlay under versions/v221; parent snapshots are references, never editing targets. Preserve native source-age and command admission separately from global static feasibility.

## Approved scope correction, 2026-10-17

Dr Sun authorized three concrete deliverables in the current conversation:
1. In plan_env, associate the physical floor independently of navigation selection and report an evidence-floor edge-guard rejection precisely. Preserve all normal selectedSurface admission and binary rejection decisions. Do not implement an escape connector, recovery exemption, or new PCT/SCAN recovery state machine.
2. Attribute the archived v217 42–62 s window using identical recorded inputs. Report edge-guard, current/historical nonterrain occupancy, and twin-cylinder-versus-torso differences as independent predicates, including their intersections and explicit denominators. A torso-only comparison does not prove full-leg clearance. Preserve old replay outputs.
3. Complete shared environmental scoring in PCT search, PCT optimization and native SCAN optimization. New scores must bypass the inherited search <5 and optimizer <=15 dead zones, while legacy mode and hard admission remain unchanged. Clearance must saturate at the target; static support-edge and solid-obstacle evidence are separate.

Version v223 owns floor association/rejection diagnostics, with the tested v221 attempt03 as source parent. A subsequent integer version owns the scoring change. Frozen versions and v221 attempt03 are retained. RL, motor limits, stop/standing logic and global replan scheduling are outside this change. Component builds and recorded-input analysis are authorized; no new physics or robot motion is included.

## Continued diagnosis, 2026-10-17

Dr Sun supplied an external critique and authorized subagents. Inline mode keeps
implementation/final checks in the main session; three read-only explorers
traced field dependencies, GPMP units and the remaining height witnesses.
Treat numerical causal assertions in the critique as hypotheses: the legacy
obstacle residual is squared before GTSAM squaring; velocity derivatives follow
the current yaw model. Preserve mathematical Jacobian consistency during any
fixed-seed-heading ablation.

v225 isolates offline height-aware single-cylinder lookup and analytic gradient
computation. Retain both centers at actual body Z; a per-floor 2-D solid table
would change stair/ceiling semantics. Measure approximation errors against the
frozen raw field. Subsequent logical versions handle measured GPMP scaling/
heading and canonical floor association. Do not change hard tolerances or move
requested body XYZ to fit an inaccurate navigation height proxy.

The measured continuation selects v226's continuous integer-anchored old-cost
view in configured shared mode, retaining full current-velocity heading and
original weights/tolerances. v227 physical-origin-only support alignment fails
its full-route gate. v228 uses verified original PCT header metadata for the
nominal lattice; no decoder, source point, selected label or height changes.
Final global references may use the existing hard-checked raw-graph fallback;
GPMP height smoothing remains separately unaccepted. No recovery protocol or
normal admission waiver is introduced.
