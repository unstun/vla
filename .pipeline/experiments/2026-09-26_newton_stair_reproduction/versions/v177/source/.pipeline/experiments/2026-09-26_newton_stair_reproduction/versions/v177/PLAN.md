# v177: Linux execution of the v176 terminal-capture change

Stage: experiment and analysis. Local source of truth: this VLA repository.
Exactly649native source files must match frozen Macv176. Linuxv175 is the tested
binary underlay; rebuild only the changed lite3_nav2_bridge profile package.
No controller, planner, PCT, BT, map, start, route, policy or other parameter edits.

Macv176 passed one original full route77.659m with6qualified measured-stop
handoffs. This does not establish repeatability. Preserve all v175 failures.
Run the recorded terminal fixture against actual Linux native tracking headers,
generated-profile tests, inherited host gates, real graph/library checks, then
freeze and run five serial original-route episodes on gpu5070ti. An admission or
infrastructure failure stops the batch; ordinary navigation failures count.

Return SHA-verified compact outcomes, full-route checks, stop proofs and provenance.
Retain heavy raw inputs/captures remotely. No stable-recovery claim unless the
declared five-trial cohort qualifies; do not pool Mac and Linux outcomes.
