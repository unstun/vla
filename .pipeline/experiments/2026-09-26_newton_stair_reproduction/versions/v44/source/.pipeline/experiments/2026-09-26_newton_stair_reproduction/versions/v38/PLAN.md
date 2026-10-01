# v38 CUDA solver graph component

Stage: experiment + analysis. Parent: frozen v37 device-selection component.
One change: replay the pinned CUDA solver call through two captured graphs,
one per state-buffer direction. Policy inference, NumPy PD, collision pipeline,
pre-integration capacity rejection, applied-force checks, finite-state checks,
200 Hz pose reads and all physical timesteps remain unchanged.

Dr Sun approved the performance comparison/optimization on 2026-09-30.
v37's naive CUDA phases reached RTF 0.5098/0.5056, versus CPU 0.5382/0.5227.
Static CUDA/CPU drift was tiny; forward closed-loop joint/action differences
were substantial. v37 CUDA is not adopted into navigation. Changing the device
alone did not solve performance. The graph component isolates the many solver
kernel submissions while preserving every surrounding safety check.

Reference: the acquired Newton v1.6.0 AnyMal example uses ScopedCapture and
capture_launch after warming lazy buffers. The fixed installed SolverMuJoCo
source uses host _step only for update_data_interval, selected 0; sleeping is
disabled. Guard these settings and reject changed state/control/contact objects
or physical dt. Do not mutate installed Newton or frozen parent sources.

The first actual integration warms the solver. Capture is dry on CUDA, without
resetting physical state or clock; restore its Python-only step counter after
capture. Later graph launches increment that counter once per actual 1 ms step.
Validate actual solver-clock continuity and solver._step==robot.steps.

Execute the same bounded continuous 4.1 s scene/commands as the v37 audit.
Compare graph vs unmodified CUDA traces, report any differences, and retain
finite/upright/force checks. Synchronized whole-phase wall time determines RTF;
method timings are not isolated GPU kernel measurements. Record actual capture
and launch counts. Source snapshot is frozen before execution, unvalidated.

No whole-episode integration, pacing, sensor/transport/navigation run, training
or hardware actuation is included. Local planner profiling is a separate audit.
