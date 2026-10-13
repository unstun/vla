# v165: repeated full-route acceptance failed
Stage: experiment and analysis. Five requested attempts were retained.
| Attempt | Outcome | Sensor path (m) |
|---|---|---:|
|01|FAILED|65.188|
|02|FAILED|74.616|
|03|FAILED|23.524|
|04|Startup aborted before navigation; unqualified|—|
|05|FAILED|23.461|

No arrival was accepted. Four navigation runs failed; one startup aborted due to
an occupied telemetry port. The fifth attempt resumed only after checking all
local addresses. All completed navigation handoffs have matching recorded stop
proofs. Neither a proof nor a successfully reused global reference implies that
a local recovery curve exists.

The original-reference reuse branch is observed in actual v165/01 generations
5-7, but the local planner still cannot issue a first curve. Native replay now
finds a5cm backward curve while holding current heading; v167 is a new candidate,
not an accepted replacement. v166 separately isolates Linux service ports.
