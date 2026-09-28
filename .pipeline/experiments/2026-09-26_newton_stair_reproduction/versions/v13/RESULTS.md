# v13 results

Removed discarded legacy seed initialization. Native build passed with unchanged
source hashes. The bounded repeated-call fixture passes twice on the captured
expired curve and once on the original 66 scans; PVA and full-curve collision
checks pass. The old implementation aborted under the same 1.5 GB process cap.

Physical `v13_building_route01` ran 89.962 s and did not repeat the v12 OOM.
It did not reach the stair goal: net horizontal displacement was 0.332 m.
At 27.3066 s the FSM published `native_replan_exhausted`. Controller hold was
published at 27.3166 s, but the backend incorrectly consumed the earlier FSM
rejection and never confirmed that hold. The robot eventually entered fixed PD
stand; this was a failed route with no terminal ledger record.

Evidence: `runs/v13_seed_regression01`, `runs/v13_building_route01`, and
`audits/2026-09-27_v12_process_exit`. The stop-reply mismatch is addressed
separately in v14; recorded stair-riser classification is addressed in v15.
