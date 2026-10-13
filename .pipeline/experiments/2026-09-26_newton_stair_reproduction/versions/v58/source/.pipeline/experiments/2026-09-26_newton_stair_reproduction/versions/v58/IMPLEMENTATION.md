# v58 implementation

The original `goalRegionMayFit` is the all-possible overload of one shared enumeration; its bounds-only behavior is retained. A* additionally applies `bodyEndpointMayBeObserved` at every enumerated exact/tolerance endpoint for positive-tolerance plane search only. A possibly observed reflected front/rear voxel pair in the conservative cylinder-center square, regardless of its occupancy verdict, retains possible eligibility. An endpoint near the measured-body waiver always remains eligible for search. No verdict is cached and no input is modified.

A negative result proves both that no exact connector endpoint can be clear and that no lattice tolerance endpoint can be clear. Every successful original endpoint needs a free front/rear cylinder query; a remote all-unknown region cannot satisfy that query. The optimistic evidence is intentionally weaker than collision or stair-support admission. Existing A* and final native validation remain responsible for all positive outcomes.

The manager, FSM, controller, optimizer, sensors, physical evidence, final goal, yaw, dynamics, minimum cruise, recovery and stop code are byte-exact v57. Only five native files differ. The paired-test switch is not a runtime parameter.
