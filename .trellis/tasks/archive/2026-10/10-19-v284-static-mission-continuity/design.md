# Design boundary

Local repository is authoritative; gpu5070ti is the execution copy. Parent is
frozen v283 (native caeea41b0dbb99ca10ae74b1cf6239535d4c2c4d25327f53988d8afe7b1393f4).
Own only versions/v284 and a separate v284 audit plus task/spec/index records.
Keep all unrelated dirty files and frozen parents unchanged.

The smallest gap is continuity: a validated static reference is invalidated by
moving-start rechecks; local hard rejections/reset remove smooth continuation;
the command owner can freeze phase and send pure yaw away from the goal.

Expected native seams: PlanOnGoalChange and PCT plugin route reuse; GridMap
local collision query and shared environmental cost; SCANReplanFSM warm seed;
TrackingNode command generation; shared StaticSolidField soft-cost method and
PCT GPMP environmental residual hook. Use the existing curve-gradient chain,
not a second map or control framework. Inspect support query ownership before
limiting WrongHeight to diagnostics in local execution. Initial global hard
admission and independent measured audits retain the exact original geometry.

Hypotheses to test: (1) the route decorator's local replan event causes new
moving-start searches; (2) common local static veto and warm reset remove an
otherwise usable spline; (3) heading hysteresis/translation scaling and expired
fallback produce nonterminal pure yaw; (4) existing soft atlas does not reflect
the exact source-wall clearance at narrow bends. Test actual owners, then fix.

Remote root /home/sun/vla_exec/static_continuity_v284; raw recordings under
/home/sun/vla_exec/physical_runs_v284. Sync owned local bytes, verify SHA equality,
build/test, return receipts, freeze, score 53, return gate, execute ten, return
compact evidence and full videos. Heavy captures/builds remain on gpu5070ti.

## Pre-run measurement definitions

Retain the v283 strict all-Free support screen unchanged for paired reporting.
Also report true gap/source-solid/raw-point margins separately, including every
WrongHeight sample. Do not label those height diagnostics as SupportGap. Pauses
use measured XY speed <0.05m/s, with initial planning wait and pauses after the
first applied XY command >0.05m/s reported separately. Report all pauses >=60s
after that first translation; the user's approximately80s symptom is not a new
mission timeout. Nonterminal pure yaw means applied XY norm<=0.01m/s and
|yaw|>0.1rad/s outside the existing configured goal XY/Z capture region. These
are measurement rules, not new navigation constraints.
