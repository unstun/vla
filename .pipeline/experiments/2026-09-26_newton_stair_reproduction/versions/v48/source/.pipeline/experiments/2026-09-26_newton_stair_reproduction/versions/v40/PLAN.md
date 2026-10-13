# v40: CPU solver graph component

Parent version: v39. Physics implementation parent: v38. Capture the same fixed 1 ms solver operations on CPU, using the deferred CPU APIC capture in Warp 1.17.0. Keep original CPU inference, PD, collision, force checks, finite-state checks, contact-capacity checks, state-buffer identities and continuous physics. No navigation or realtime pacing change.

First gate: identical original-CPU closed-loop trace for all 200 recorded 50 Hz rows, plus no physical advancement from dry capture and matching step counters. Then measure actual RTF in the same Building scene. Retain failures. No CUDA adoption from failed numerical parity evidence.

Primary implementation API: https://nvidia.github.io/warp/v1.17/user_guide/runtime.html#cpu-apic-graph-capture-and-replay-experimental
