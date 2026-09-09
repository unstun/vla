# Design

Use the upstream model server and MuJoCo application as two isolated processes
on rented4090. A task-owned harness may submit the original UI instruction
through `/ws` and collect existing camera/state outputs. Model decoding,
WebSocket navigation client, capture-pose alignment, MPC and robot dynamics
remain upstream-owned behavior. Rendering/recording additions must be isolated
from observations and control.

The pinned pristine checkout lives under `references/upstream`; only the dated
experiment working copy is editable. All final source and evidence return to
the local repository. Preserve the existing Isaac Sim workload and other VLA
environments. Use original BF16 and checkpoint-resolved visual settings.

Native stop, task arrival, forced termination and inability to move are separate
observations. Three repetitions use the same original scene/start/instruction;
results do not constitute a standard benchmark or language comparison.
