# v219: request global replan while local replanning fails

v217 prevented the prior fall but exhausted six ordinary retries at the stair.
Its request came only after curve expiry and canceled the usable route owner.
Add the missing direct SCAN planning-result snapshot and an event request to
PlanOnGoalChange after 0.75 s of consecutive unsuccessful local rounds. Bind
requests to the exact current Path header; ignore old-route and duplicate requests.
A successful local round or new route clears the failure interval. Keep the
current executable curve while global planning runs. No timer-driven planning
while local rounds succeed. Keep v216 supported transfer, geometry, speed,
terminal and existing ordinary failure/retry rules. The v217 timeout remains a
fallback. Native planner changes only report existing boolean outcomes.

Test native result publication, snapshot revision isolation, timely request,
no cancellation of usable curves, installed BT request/cancel/goal binding.
Run on 5070Ti and retain v217 evidence. Then run the original full route and
render its real captured states. Local source and SHA-256 receipts are required.
