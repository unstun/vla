# v128: notify Nav2 when native safety stops its controller

Native parent: v114 (no MPPI adaptations). Host parent: v125.
Smallest gap: an asynchronous negative native safety proof latches zero output,
but computeVelocityCommands keeps reporting normal zero commands until the
10-second no-progress timeout. Surface that existing negative verdict as a
PlannerException on the next controller tick, allowing the existing BT to begin
measured-stop recovery. Preserve all source ages, collision verdicts, ownership,
physical-stop proof and retry counts. Normal cancellation and goal holds remain
zero-command holds. Do not change route geometry or shorten any timeout.

Owned production path: src/scan_nav2_controller/src/controller.cpp. Retain the
negative candidate proof that caused a pre-activation stop; the stopped tick
checks that proof. New owner admission clears the old proof only after the
existing measured-stop gate. Test both negative-proof delivery orderings and
verify no new owner/late positive proof can bypass the stop gate. Run the new
tests against the unchanged original install before applying the change.

This fixes notification latency, not every recovery failure; original route
admission can still reject a new reference. Freeze and preserve each physical
pilot before any further logical repair/version.
