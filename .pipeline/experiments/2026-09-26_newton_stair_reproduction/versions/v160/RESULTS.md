# v160 local result

Stage: experiment and analysis. Source frozen3647pairs/618inputs.
The actual parent plugin regression fails for0.21rad residual yaw. v160keeps
correcting within the old acceptance band until half-tolerance capture, then
revokes normally. Original GoalChecker0.25rad and causal stop proof remain.
37unique controller tests pass (40colcon entries), unchanged terrain1,18host
tests, actual loaded library and15sgraph pass.

| Attempt | Native outcome | Sensor path | RTF | Result |
|---|---|---|---|---|
|01|FAILED|35.235m|0.964825|Mid-route progress timeout then PCTno_route; goal capture never reached|
|02|FINISHED|77.571m|0.999814|Original start to goal,5qualified stop-before-replacement handoffs, finalPDhold|

Both closed raw trials remotely verified; archive receipts in their result
folders. No falls recorded. Trial02actual frame0is original crouched pose,
continuous native simulation0–146.007889s. Its densely recorded body path is
78.699m; this differs from the10Hzsensor path
above because of sample rate. FinalXYerror0.165869m; final
yawerror0.102538rad within unchanged0.25rad.

Local cohort1/2arrivals is not reliability acceptance. The recorded corner
steering component remains separately tested; do not claim it triggered when
it did not. v161rebuilds exactly the same646native source files on Linuxfor
five original-start trials, with no changed planning algorithm.
