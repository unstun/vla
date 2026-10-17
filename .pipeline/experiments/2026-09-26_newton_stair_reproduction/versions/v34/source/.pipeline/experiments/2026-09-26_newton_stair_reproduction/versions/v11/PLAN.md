# v11: propagate native replan exhaustion to the owning task

Parent: v10. Stage: experiment + analysis. Independent repair authorized by
Dr Sun; no terrain, controller or speed changes.

The native FSM currently discards its target after exhausting retries without
notifying P2B. Publish an existing `rejected` admission with reason
`native_replan_exhausted` and the current identity. Do not claim physical hold.
The actual `p2b_backend_ros.node.RosScanPort` closes the command gate and
publishes zero only for this same-owner FSM notice, unless cancellation is
already pending. Existing runtime fault handling must request cancellation,
obtain controller hold and measured quiescence, then emit a failed terminal.

Owned changes: a new native candidate's `scan_replan_fsm.cpp`, the selected
local backend ROS receiver, and its runtime-source identity receipt. Preserve
the receiver preimage and original archive hash; freeze changed source and
receipt before execution. Do not edit the archived scan28 source or sibling
repositories. Existing stop-flow implementation is reused, not replaced.

Required checks: baseline receiver test fails; current-owner notice closes the
gate and zeroes commands; stale/foreign/no-owner/ordinary admissions do not;
cancel precedence remains; actual native FSM publishes once after exhaustion;
existing stop flow produces failed outcome only after its normal evidence
checks. Late notices must not close a newer command. Keep full route acceptance
separate from failure reporting.
