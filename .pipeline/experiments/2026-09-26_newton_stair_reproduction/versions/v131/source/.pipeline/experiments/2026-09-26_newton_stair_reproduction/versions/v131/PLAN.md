# v131: bounded mission recovery allowance

Parent frozen v130, original control v114. Prior complete comparison recorded
legitimate third controller stops exhausting the custom outer budget of2.
The actual installed RecoveryNode/WaitForScanStop probe confirms3failures then
success cannot reach its fourth navigation attempt with this budget.

Change only custom navigate.xml outer retries2to6, matching the count in the
pinned Foxy regular replanning-and-recovery tree. The different stock round-robin
tree has outer2and inner4; do not claim the custom tree matches all stock behavior.
Six retries permit at most7navigation attempts. Every retry still requires the
original measured-stop proof and a freshly admitted safe trajectory. Missing
stop proof must end recovery immediately. Do not reset/replenish the mission
budget, change safety limits, or keep retrying indefinitely.

The shared v131 host recorder also subscribes read-only to the existing
/nav2_scan/stop_evidence topic for both arms. This records the actual gateway
proof before each new owner; it grants no motion permission and changes no
producer. Record DDS arrival ordering separately from proof source stamps.

Actual installed BT component cases:3failures then success onattempt4; persistent
failure bounded at7attempts/6proved recoveries; unproved stop ends after1attempt.
Then one pilot and a fresh predeclared six-per-arm same-host comparison. All
earlier failures and pilots stay excluded from that primary comparison.
