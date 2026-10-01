# Diagnostic target replay after device/graph comparison

Same Building/URDF, one continuous state, fixed 1 ms PD/physics and all original
capacity/force/finiteness guards. Repeat the 0.1 s zero-policy warmup. Then feed
the exact 200 recorded 50 Hz joint-target rows from `v37_cuda_attempt01/trace.json`
through the existing PD motor loop for 20 substeps each, without fresh policy
inference during the measured phases. Do not reset state between phases.

Cases: `v37_cuda_target_replay` and `v38_cuda_solver_graph_target_replay`.
This controls the target inputs while measuring CUDA eager/graph numerical
differences. It is not a closed-loop locomotion or end-to-end speed acceptance.
The source-policy actions are not claimed as new inference outputs. Trace action
and policy-input fields retain warmup state and must not be scored as measured
phase policy calls (there are zero).

Before execution, a diagnostic parity gate is declared: maximum body-position
delta <=0.001 m and maximum joint-position delta <=0.001 rad, over the recorded
measured trace. Require both cases' finite/upright/force/counter/step checks.
Report exact comparison and actual maxima; a failed provisional gate is retained
without relaxing it. Actual wall timings remain recorded, but the approved
closed-loop four-case comparison remains the speed evidence.
