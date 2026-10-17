# v214: display the complete v212 fall recording

The unchanged v213 renderer expects a Nav2 terminal result. This recording stops
on the original physical fall detector before Nav2 returns a terminal action.
v214 accepts that recorded physical outcome without inventing a Nav2 failure.
It labels the actual final frame physical fall (simulation stopped), retains
all original states/timing and executes zero physics. v213 remains preserved
as an unexecuted display package. All other v211/v213 appearance, camera,
streaming, causal frame and curve checks remain unchanged.
