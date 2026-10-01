# v14: Keep admission replies scoped to their consumer

Parent: v13. Native SCAN remains `scan51_seed_init_v13`.

The v13 physical failure published an FSM rejection, then the controller's
confirmed hold. `request_stop` consumed the earlier FSM rejection because the
common wait helper allowed any consumer's rejection. The adapter consequently
waited forever for a hold it had already received. Require the requested
consumer for every admission status; preserve identity, controller-hold and
measured-quiescence checks.

Acceptance: replay the exact recorded admission order through the actual
receiver; test absent, foreign and wrong-consumer replies; rerun the existing
stop-flow tests. A later physical failure must release ownership and record a
failed terminal result after measured stillness. This change does not repair
stair reachability.
