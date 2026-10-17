# v230: local obstruction coordinates change subsequent PCT planning

Status: validated component and recorded-input gate, parent frozen v229.
No new physics, training, robot actuation or accepted-source promotion.

## Actual installed planner feedback experiment

The installed PCT plugin uses its real service client, mission context, A*/GPMP,
repair and publication gate. A typed wire fixture introduces a local disk
obstruction of radius 0.15 m on the first returned reference. It is an explicit
controlled service fixture, not a captured live sensor/NativeWorker experiment.
The native LIVE implementation is independently checked on recorded inputs below.

| Returned reference | Continuous XY distance to obstruction center | Length |
|---|---:|---:|
| Initial | 0 m | 3.503847 m |
| Confirmed blocked | 0.179713 m | 3.524403 m |
| Subsequent unknown observation | 0.179713 m | 3.524403 m |
| Newer exact Free observation | 0 m | 3.503847 m |
| New mission, unknown observation | 0 m | 3.503847 m |

All preserve the initial canonical goal exactly. Cleared/new-mission pose
geometry equals the initial output byte for byte; unknown geometry equals the
blocked output. Independent continuous segment distance, rather than vertex
sampling alone, confirms the detour. A live-blocked terminal cache is rejected
and never republished. Source/mission binding, exact newer Free, stale/unknown,
TTL, different floor/heading, persistent-vs-per-call reset and no-old-start-
connector sampling tests pass. The five actual returned CSVs and their hashes
are retained in results/feedback_output/ and results/feedback_metrics.json.

## Reused implementation

The existing Header -> BT ComputePath trigger stays intact. Each managed PCT
request rechecks a bounded forward/local portion of the current reference and
outstanding witnesses, and checks the candidate after solving. CheckTraversability
now implements its existing STATIC_AND_LIVE mode. The native provider returns
exact typed decisions from the original reactiveOccupancy/twoCylinderQuery,
immutable map revision, observation time and stable navigation/surface/physical
source fingerprints. It never infers StaticObstacle from a binary refusal.

Only fresh native StaticObstacle creates a directional, height-associated
planning constraint. Memory is mission/epoch/source-bound, capped at 128 poses,
expires after two steady-clock seconds, and is reconsidered on a strictly newer
Free at the exact stored XYZ/yaw. Unknown/stale/outside cannot clear it. A Path
refresh preserves it. Queries use <=384 reference/witness poses and a 3 m forward
reference radius; actual native coverage remains authoritative. No new mapper,
DirectIO/MotionExchange session protocol or RL change was introduced.

Persistent feedback and per-request static repair are separate. Both affect
existing A* transition checks and derived GPMP costs/gradients. Persistent
feedback additionally checks final translation/rotation/connector samples,
including all cache returns. Per-request static repairs use the fresh native
final verdict; an old search mask cannot overrule newly checked static geometry.
If a static provider reports a solid collision, four undirected graph headings
are explicitly queried (<=800 extra samples) instead of declaring every heading
blocked. Candidate budget remains three. This extra batch does not grant any
unqueried heading clearance.

## Native recorded-window and unchanged Building gate

All 126324 original v217 queries plus three critical queries retain their binary
verdicts and every independently recorded occupancy predicate. Typed LIVE also
matches every original binary decision and every independently explained typed
reason where available. Main-window typed first decisions:

| Verdict | Queries |
|---|---:|
| Free | 75707 |
| UnknownObstacle | 7423 |
| StaticObstacle | 2267 |
| UnknownSupport | 12855 |
| SupportGap | 10303 |
| EdgeClearance | 17769 |

The additional three critical queries are EdgeClearance. The native stable
source IDs are nonempty and invariant across recorded snapshots. The exact
48.10519028 s platform remains 1.5580306959152221 m and rejects
0.28284271247461906 < 0.35 m. Nothing grants support at that edge.

The actual installed Building reference remains identical to v229: shared mode
admits on the first request, 0/3821 native-static rejections, exact XYZ goal,
raw PCD solid margin +0.056539 m, extra edge margin +0.141488 m. Entire shared
call measures 0.730794 s versus v229 0.727385 s. The ~0.35 s target is still not
achieved. Legacy geometry also remains identical (729 poses, 4739 samples), but
its single measured call is 0.394160 s versus v229 0.209734 s; these one-shot
measurements do not establish a latency distribution or its cause.

## Verification, failed attempts and provenance

Final attempt04: nine packages pass; 174 colcon records comprise 154 distinct
cases plus 20 wrappers, zero errors/failures/skips. Full existing freshness,
tracking, terminal, stop/epoch, immutability, scoring and profile tests remain.

Earlier attempts are retained, not relabeled passing. Attempt01 exposed test
executor cleanup order and fixture initialization/terminal comparison errors.
Attempt02/03 exposed a real static-repair regression from imposing old per-call
masks on final output, plus a test point in an invalid -100 m cell. Final
implementation separates persistent admission from authoritative static recheck,
uses explicitly checked graph headings and fixes the fixture. Their original
source revisions, XML and full test stdout remain in results/build/attempt*/
and results/source_revisions/.

results/sync_gate.json verifies all 314 composed source files against the local
overlay and parent. Compact return: 244 files, 2686692 bytes, with no CMakeFiles,
object files or build cache. Full replay CSVs remain on gpu5070ti under
/data/sun/vla_mppi_20261009/blocked_feedback_v230/replay_output01/, with returned
SHA-256/size and replay tools. Rebuild interfaces/provider/client together:
the service adds source_identity. The local repository is the source of truth;
remote workspaces are execution copies only.

This gate does not establish actual NativeWorker-to-managed-PCT closed-loop
sensor performance or physical navigation reliability. The new wire behavior,
installed PCT route changes and recorded native decisions are tested in their
stated component scopes. v219/v220 remain the physical source/display pair.
