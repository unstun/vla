# v160: tighter yaw capture before irreversible goal hold

Stage: experiment and analysis. Parent native/host v159. The v159 local trial
traveled77.078m but failed after requested_goal_reached. First measured stop
proof arrived at127.146751404s, after yaw drift exceeded the original0.25rad
goal tolerance. There were288 valid stop-proof deliveries; the goal latch
prevented further correction until progress abort. This is not missing proof.

Use half the existing configured yaw tolerance for entering goal hold and for
the tracker yaw deadband. Keep the final GoalChecker full XYZ/yaw acceptance
unchanged, plus causal1s stop proof, owner revocation, fresh data and collision
validation. This is a stricter capture target, not a larger acceptance region.

Red/green: replay observed0.21rad within-goal approach through the actual plugin.
Parent cancels and returns zero; candidate must continue checked yaw correction
without owner cancellation, then zero/cancel at0.10rad and require physical proof.
Retain existing outside-tolerance rejection. Build controller overlay, verify
actual loaded library, freeze, then original-start full physics and archive.
One success is not reliability. Only after local qualification run Linux repeats.
