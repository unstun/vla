# v11 results

The receiver baseline fails and the repaired callback passes four tests. Seven
existing stop-flow tests pass against the actual selected runtime. Native
`v11_native_notice02` verifies the real FSM publishes one identity-matched
rejection at retry exhaustion, is quiet before the threshold and without an
owner, and does not claim physical hold. Attempt01 is retained: diagnostic
ROS domain 234 exceeded the UDP port range; attempt02 uses 229.

No physical endpoint completion is claimed by these tests.
