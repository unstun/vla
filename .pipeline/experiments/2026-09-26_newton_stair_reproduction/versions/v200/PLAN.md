# v200 — physical terminal completion inside FollowPath

Parent: v199; execution-state wire/ROS interface: frozen v198.

GoalChecker previously reported success from pose and low odometry velocity,
while the external driver waited for PD stand. This version keeps FollowPath
active until typed execution feedback proves two continuous seconds of
FIXED_STAND, PD ownership, quiet measured motion and a current zero command.

- Source timestamps measure the hold duration. Duplicate, foreign, nonfinite,
  frozen and stale samples cannot extend it; gaps restart it.
- Cancellation, new goals and departure from terminal tolerance reset the hold.
  Same-goal path refreshes retain the window.
- ControllerServer computes the current phase before checking movement progress.
  Terminal waiting resets SimpleProgressChecker; ordinary movement still uses it.
- A separate 10-second steady-clock deadline fails terminal waiting.
- Remove the generic outer RecoveryNode and Wait. FollowPath failures propagate
  directly, including terminal timeout, instead of replaying the whole route.
  This deliberately disables all implicit whole-task retries for now.
- The fixed 1 Hz planning child is retained until the later event-driven planning
  version; no dynamic obstacle masks or PCT algorithm changes are introduced.

Build and component regressions only; no new full-route experiment. This is a
versioned native overlay, not a claim of whole-system physical validation.
