# Real-time budget audit

Stage: experiment + analysis. Dr Sun requested simulation time to match real
time as closely as possible on 2026-09-30. Target: one simulated second per
wall-clock second, measured from the actual solver clock. Keep the existing
1 ms integration/joint-PD step and 20 ms policy period. Do not change timestamps
to disguise slow execution or alter collision geometry to improve the score.

First measure the frozen v35 Building physics path on gpu5070ti, then account
for sensing, transport and planning. The current model is explicitly finalized
on CPU and uses MuJoCo-Warp with Newton contacts for Building; having a 5070 Ti
in the host does not make this physics run GPU accelerated.

The initial audit is bounded: one robot state, five zero-command warmup policy
steps and 100 zero-command measured policy steps (about 2.1 simulated seconds
total), no route, no ROS navigation stack, no hardware actuation. It uses the
existing pinned policy and Building, with recorded pose observation every five
physical substeps. No new weights or private controller bytes are transferred.
Instrument original calls without changing their inputs, results or timesteps.

Return the exact profiler source/hash, module/input identity, timing samples,
solver elapsed time and wall elapsed time to this local directory. This first
result is a physics-only ceiling; it cannot establish real-time performance of
the full navigation/sensor stack. Any behavior/device/pacing change gets the
next logical integration version after v36 is frozen. No long navigation run
is authorized by this audit.
