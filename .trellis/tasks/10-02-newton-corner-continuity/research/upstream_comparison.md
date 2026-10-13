# Pinned SCAN upstream comparison

Verified 2026-10-02; planning evidence, not a native change.
Pin: 348e8a590a50a5a6bbab8d8c6dcfd171f009be26, Apache-2.0.

Upstream reference regeneration sets have_new_target_. callReboundReplan passes
that flag to the manager, selecting fresh polynomial initialization. It does not
explicitly clear an accepted-owner or feasible-window cache; these are local
v48/v47 additions. Source: [pinned FSM](https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/plan_manage/src/scan_replan_fsm.cpp#L197)
and its [replan call](https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/plan_manage/src/scan_replan_fsm.cpp#L827).

The manager's alternative branch samples/resamples the remaining curve and
appends a polynomial extension; it lacks the local target_connector rejection.
The inspected code then applies linear-Z reference. Those unchecked extension/Z
behaviors were deliberately excluded from v48. Source: [pinned manager](https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/plan_manage/src/planner_manager.cpp#L99).
Local archived manager SHA is verified against versions/v48/upstream_identity.json:
d5daf9ac96432e7b5334c4819f5d8688d046f366a48bd8f6eeac8a7ccda08863.

Local provenance: v47/changes.patch introduces feasible-window invalidation;
v48/changes.patch adds invalidateWarmStart and target_connector. In the captured
first failing round, rejection is identity_or_owner. target_connector appears
only in the diagnostic restored-binding probe, not as a direct callback result.

Compatibility plan retains unsafe-connector rejection and full final gates,
while refining ownership/window handling for a periodic same-command refresh.
This is a local improvement, not exact upstream restoration.
