---
origin: ai_only
reviewed: false
status: surveyed
---

# TIC-VLA simulation inference: upstream execution path

Date: 2026-09-08. Scope: read-only source and paper inspection; no simulation,
training, remote deployment, or robot actuation was started.

## Answer

TIC-VLA has a released closed-loop simulation path in DynaNav, built on Isaac
Sim. A pretrained checkpoint can be evaluated through that path without first
retraining it. This repository has offline Orin inference and asynchronous
replay evidence, but no DynaNav closed-loop result was found in its experiment
records. A successful model forward does not establish a simulation result.

## Sources and identity

- [Paper, v1](https://arxiv.org/html/2602.02459v1), sections 3.2, 3.4 and 4.2.
- [Canonical repository](https://github.com/ucla-mobility/TIC-VLA), branch main.
- [DynaNav instructions](https://github.com/ucla-mobility/TIC-VLA/blob/main/DynaNav/README.md).
- [Public example](https://github.com/ucla-mobility/TIC-VLA/blob/main/DynaNav/configs/benchmark_example.yaml).
- Local source inspected at commit
  `9fa6f8b66b9e121d5df5df071297bba8e5353ebb`; its worktree was clean.
- Local source: `references/upstream/2026-08-20_tic_vla/source/TIC-VLA/`.
- License: UCLA Academic Software License; see the existing
  `references/upstream/2026-08-20_tic_vla/repository_manifest.yaml` for terms,
  source provenance, pinned model revisions, and checkpoint SHA-256.

## How the released simulation loop works

1. Isaac Sim supplies an egocentric RGB image history, robot pose and velocity.
   The task configuration supplies the natural-language instruction.
2. `DynaNav/ticvla.py::predict_async` starts VLM reasoning on a background
   executor and reuses the latest completed reasoning KV cache. The first
   cache is a blocking initialization step with a 30-second wait timeout.
3. The action expert consumes the current image, cached reasoning, body-frame
   velocity/yaw rate, reasoning-relative displacement, and delay. The inspected
   model config sets `action_dim=2`; the consumer and retained outputs use
   `(1,30,2)`. Older comments describing three components are not the executable
   tensor contract.
4. The behavior script selects a lookahead point from the waypoint sequence,
   converts it to bounded velocity commands, and executes them in simulation.
   Nova Carter uses a differential-drive controller. Spot uses
   `SpotFlatTerrainPolicy` with base commands `[vx, vy, wz]`.
5. Updated images and state feed the next control cycle. The benchmark records
   navigation error, success, path length/SPL, and collision indicators.

Source anchors in the pinned snapshot:

- `DynaNav/behavior/nova_carter_test_ticvla.py:790`: observation/state assembly;
  lines 813-826 transform world displacement into the reasoning-start body frame.
- `DynaNav/ticvla.py:891`: asynchronous prediction;
  line 289 sets the two-dimensional action output.
- `DynaNav/behavior/spot_test_ticvla.py:1424`: model call and lookahead tracking;
  line 1154 forwards base commands to the locomotion policy.
- `DynaNav/benchmark.py:266`: configured success threshold;
  line 311 constructs the per-episode result.

## Public example versus paper experiment

The paper reports an L40S simulation evaluation with a 10 Hz action policy and
0.5 Hz asynchronous VLM reasoning. These are author-reported settings, not
measurements on the user's RTX 5070 Ti. The public behavior calls the action
path synchronously inside the simulation update; its 10 Hz comments do not
establish real wall-clock throughput on another GPU. The source derives delay
from frame counts divided by 30, so a reproduction should retain both
simulation time and wall time and report the real-time factor.

The example YAML has four Nova Carter episodes: hospital, office, outdoor and
warehouse, each with 20 people. Spot has a separate public behavior script.
Neither is a Lite3 simulator integration. The example's success threshold is
1.5 m, whereas paper v1 describes stopping within 1 m; do not label the example
run an exact reproduction of the paper table.

## Minimal first execution proposal

Use the pinned upstream source and pretrained checkpoint with Isaac Sim 5.0.0
and the repository's test dependencies. Configure `.env.testing` paths in a
task-owned execution copy. The original smoke entry is:

```bash
source .env.testing
CUDA_VISIBLE_DEVICES=0 DynaNav/run_benchmark.sh DynaNav/configs/benchmark_example.yaml
```

The explicit device override matters because the pinned launcher otherwise
defaults to GPU index 1. For an initial resource probe, derive a separately
named one-episode YAML from the public example and label this reduction as a
local modification; preserve the original file. Keep a video, raw model and
controller logs, result JSON, timings, memory samples, source/config/checkpoint
identities, and exit status locally before reporting success. Start with Nova
Carter, then the upstream Spot controller; a Lite3 port is a subsequent
interface task with pinned locomotion dependencies.

The previously quoted approximately 2.1 GiB is model-side memory from an Orin
single-image run. It excludes the simulator's scene and renderer requirements
and does not establish that every DynaNav scene fits on the 16 GB RTX 5070 Ti.

## Existing local evidence relevant to timing

The single-image serial Orin forwards averaged 13.833 seconds including VLM
reasoning; this is not an asynchronous action-loop period. The later
`orin_p1/p1_async_replay_1plus100.json` under
`.pipeline/experiments/2026-08-20_tic_vla_lite3_controller/` records a 19.266-second
first-cache wait followed by 100 finite, correctly shaped fast-path outputs,
with mean call time 0.217848 seconds and p95 0.215637 seconds. Its explicit
claim boundary is offline asynchronous replay with no sender or motor path.
Neither evidence set is a DynaNav closed-loop run.

## Follow-up execution

The subsequent user-authorized RTX 5070 Ti hospital compatibility trial completed.
See [the scoped result](../experiments/2026-09-08_tic_vla_dynanav_5070ti/RESULT.md).
The survey above records the pre-execution state; the new result does not
constitute complete paper reproduction or Lite3 integration.
