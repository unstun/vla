# v85 separated mapping / execution / sensor veto prototype

Parent: v84 recorded native map investigation, original v82 map implementation.
One change: an executable three-thread component prototype demonstrates separate
sensor-veto, map-processing and 30 Hz execution-decision lanes. It is deliberately
not connected to the robot command publisher or selected as navigation runtime.

The veto only rejects. A clear sensor observation cannot make an old map current,
clear an earlier unmapped hazard, revive a cancelled owner, or grant support.
The map lane retains every distinct observation and uses original native map
checks. Existing 250 ms freshness is an additional mandatory execution gate.
The component's decisions are evidence about scheduling/ownership, not completed
physical control, braking qualification, or a navigation performance result.

Use native transient-obstacle samples to exercise the direct sensor veto and
show that the map-only latest-slot negative from v84 is still blocked. Validate
fresh/stale/future/unpaired/malformed input, retained hazard, new evidence,
cancellation, ownership replacement and late old-owner results. A controlled
650 ms map stall must not prevent sensor processing or execution decisions;
execution must fail closed when its map ages, even with fresh incoming sensors.
