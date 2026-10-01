# v37 device-selection component results

Frozen source: 5,796 files. Executed on gpu5070ti in the dated
`audits/2026-09-30_gpu_device_compare/` comparison.

CPU default preserves the original 200 closed-loop state/action/target/torque
trace rows exactly. Warm-step RTF is 0.538210 / 0.522741 (zero / forward).
CUDA eager RTF is 0.509826 / 0.505602: device selection alone is slightly slower.
Original per-step capacity, force mapping, finiteness and upright checks pass;
CUDA forward closed-loop trajectories differ substantially from CPU.

Status: bounded device component exercised; CUDA not adopted into navigation.
Full episode remains v36. See the audit's RESULTS.md for all raw identities,
return verification and v38 graph/numerical evidence. No whole-stack acceptance.
