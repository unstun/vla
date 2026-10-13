# Diagnose the latest Mac heartbeat and frequency failures

Stage: experiment + analysis. Dr Sun requested root-cause investigation after
reviewing the latest Mac video. Continue the existing Mac task inline. This is
diagnostic analysis, not a planner/backend repair or a new navigation version.

Use both immutable captures, exact frozen native v63 and v59 backend behavior.
Stream verified archive members; leave bulk and extracted replay fixtures at an
owned private/tmp root. Return compact measurements, source references and
reproducible analysis/replay scripts. Keep existing heartbeat, goal, yaw, PVA,
stair support, safety and stop contracts unchanged. Do not use gpu5070ti.

Reproduce the recorded failures through original round parsing and exact
command identity matching. Ranked hypotheses shown before probing:

1. Backend heartbeat callbacks are delayed by applied-state I/O or Python/ROS
   scheduling. In particular, /state includes complete PCT route history and
   grows to 1.5MB. Predict matching raw commands continue during callback gaps;
   exact full-state serialization can delay heartbeat work in the same process.
2. Cold seed/optimizer recovery and nested input/cloud refresh dominate tail
   rounds. Predict stage profiles show these rather than final-goal search;
   report inclusive scopes without adding overlapping durations.
3. Timer scheduling/input callbacks and Mac CPU/emulation contention consume
   capacity outside measured solve time. Predict missed wall slots persist
   despite many short solves; absolute deadline phase should rule out a simple
   timer-quantization cap.

Measure identity-bearing raw receipt, accepted heartbeat and body callback
timelines around each terminal fault. Check whether a slow solve occurs then.
Measure state field sizes and replay the exact serializer on the same cached
amd64 ROS image, plus a minimal same-process heartbeat probe using original
gate rules. Diagnostic isolation may remove route history from a copied payload
as a single-variable counterfactual; never change production state or protocol.
Separate demonstrated cause, strong evidence and remaining trace gaps. A
minimal replay establishes its seam only, not full physical repair acceptance.
