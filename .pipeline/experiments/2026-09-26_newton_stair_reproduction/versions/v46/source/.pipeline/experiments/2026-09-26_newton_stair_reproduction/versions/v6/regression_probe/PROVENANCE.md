# Native continuation regression caller

Derived from the frozen v5 frontier audit caller. The native manager/FSM source
is compiled from the selected build without rewriting it. The original accepted
spline and PCT route are deserialized from original ROS messages. Stop automatic
FSM timers only during frozen-state inspection; map subscriptions remain live.

The continued-planning call occurs before the separate direct-manager check so
that a successful direct call cannot replace the original captured local
trajectory and create false continuation evidence. Check actual returned
trajectory boundary PVA and complete collision coverage before negative cases.
The stale case advances only the test clock by 0.5 s; it does not restamp inputs.
All negative tests call the native manager/FSM, not a copied boolean predicate.
