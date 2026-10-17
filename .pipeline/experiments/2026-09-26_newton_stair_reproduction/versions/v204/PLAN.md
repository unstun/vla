# v204 — restore v196 task behavior on the simplified architecture

Restore only the three reviewed contracts: first successful PCT terminal pose
and optional-heading semantics; same-task retained-route fallback and terminal
approach suppression; six ordinary retries with Wait 1 s, excluding terminal
settle timeout. Keep the 1 Hz planning child, native PCT, LocalMotion, sole Twist
publisher, two-second physical terminal completion and unified terrain unchanged.

Task start/end metadata travels once between the HTTP adapter and navigation's
PCT plugin. This carries request identity and whether yaw was explicitly supplied;
no planning runs in MissionBridge and there is no per-plan callback to it.
Canonical goal and cached route live exclusively in the native navigation policy.
A context generation rejects results crossing cancellation/new-task boundaries.

Foxy FollowPath has an empty action result. Record failure classification under
the actual FollowPath UUID before abort; the BT queries that identity to exclude
only terminal-settle timeout from the original RecoveryNode/Wait flow. Do not
infer failure cause from a reset controller phase or uncorrelated topic receipt.

Use frozen v196 code as the oracle for goal/cache traces. Exercise the actual
recovery BT and typed failure transport, including ordinary exhaustion, terminal
exception, cancel/new task, explicit zero vs omitted heading and near-goal refresh.
Build/component regressions only. No physical/full-route experiments.
