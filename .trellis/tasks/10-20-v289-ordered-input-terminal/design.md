# Behavior and ownership

Smallest gaps: late already-taken body messages must not poison newer state; goal completion must not require2cm positioning; negative solver returns must not borrow an evaluation count as accepted descent; lifecycle probes must not be starved by unrelated work.

Primary code owners: BodyTimeBuffer plus GridMap/FSM input callbacks; TrackingNode plus Controller completion; reactiveOccupancy measured-trunk classification; BsplineOptimizer and its existing LBFGS callback interface; MissionBridge liveness. A-star/ENV geometry, PCT ownership, sensors and policy remain byte-identical.

Retain work_mutex callback guards and guard refreshSensorInputs itself with the same recursive mutex. Both direct callbacks and manual drains feed the same per-consumer monotone body buffer. A superseded message is an ignored insertion, not malformed input; callers leave existing live state intact and must not enqueue the old pose into the mapper. Invalid stamps/future overflow retain ordinary failure and all freshness bounds remain. Installed Foxy lacks add_callback_group, so do not assume a modern API or add an unreviewed multi-executor framework.

Controller completion uses its original0.25m position/yaw contract. Tracker inside capture stops once yaw aligns; while yaw differs it applies the existing proportional body-frame centering only outside a0.05m gait dead zone with smooth decay and0.15m/s cap, plus yaw. No2cm braking gate.

Restore original measured-trunk hook, preserving observed-obstacle precedence and support/freshness. Important audit finding: original measuredTrunkQuery only clears uninflated Unknown, already Free in v288. Restoring the hook alone cannot be claimed as a13-event fix; classify the actual witnesses before any additional correction.

LBFGS recovery must demonstrate actual cost descent, not more function evaluations. A finite lower-cost evaluated trial can be retained even if Wolfe acceptance failed, but only after the original hard checks; this is the user-requested best_q/best_cost contract, not a claim that the trial was solver-accepted. Initial cost is captured once and best finite variables/cost are reset per solve; record finite objective/gradient candidates in the existing callbacks, preserve cancellation, restore q/cps before unchanged whole-curve/dynamic checks. The current library calls progress inside line search with k=0 and comments out accepted-step progress; inspect and test this exact seam rather than assuming upstream semantics.

Health: preserve1s failure semantics and actual exit evidence. Inspect old response contexts; isolate probe completion from busy action/default groups and avoid unnecessary probe flooding only if reproduced. No timeout relaxation or suppression of failed graphs.

Local version/audit is truth; remote /home/ubuntu/sun/vla_v289_20261020 is private execution. Freeze sources after clean full ABI build/tests, then one serial53timing batch on an agreed quiet host. Independent audits and tenzero-step preflights precede physical manifest/local return. Tenphysics once; all later analysis/render uses unchanged recordings. Failed acceptance remains failed and no baseline is promoted automatically.

Effective bridge ownership: v288 physical execution overlays the v248 MissionBridge readiness delta. Merge that existing ACTIVE contract into the v289 main bridge and remove the redundant runtime overlay. Final source identity/preflight must verify the loaded Python module exactly equals native/src. Added three original readiness tests are part of the qualified package suite.

Latest resource steering: Dr Sun stated there is no quiet window and requested continuing under load. Run the frozen53 cohort with the unchanged2CPU quota and continuous load recording; do not stop other projects. This supersedes the quiet-host condition only, and does not waive the<=1.5s acceptance threshold.
