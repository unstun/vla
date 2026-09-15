# LightNav-0 BF16 with physical Lite3 on the rented RTX 4090

Status: integrated in the pinned MuJoCo demo and tested on 2026-09-10 UTC.
One navigation trial completed; the requested trashcan was not reached.
This is simulated Lite3, not a physical-hardware deployment or benchmark score.

## Watch

- [Navigation film](media/navigation01/lite3_navigation.mp4): 9.15 seconds,
  preserves the 9.146-second instruction-to-termination wall interval.
- [Walking-only smoke](media/lite3_walking_smoke_sim_time.mp4): 14 seconds of
  simulation time, supplied commands, no LightNav inference.
- [Final view](media/navigation01/final.png).

## Model and robot identity

- Navigation: official `LightOriginsHQ/LightNav-0`, revision
  `826dc5fbfa37afa8293d2e336d329b6ffc0bfb64`, vLLM 0.19.1, BF16.
  Actual startup reports `dtype=torch.bfloat16`, `quantization=None`.
- Walking: user-selected v12 `model_149999`, FP32 ONNX on CPU, 50 Hz.
  SHA-256: `7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b`.
- Robot: pinned official Lite3 MJCF and meshes, physical torques and contacts,
  1 ms MuJoCo substeps; no kinematic base updates after reset.
- The inherited LightNav model/client/MPC source is unchanged except for the
  previously recorded capture observer. New behavior is in `robots/lite3.py`
  and its CLI selection. Snapshot recording counters were exposed to the harness.
- The robot camera is torso-mounted at (0.24,0,0.08) m, horizontal, 480x270,
  vertical FOV 79.865 degrees. Different dynamics and camera height mean this
  run is not a controlled robot-only ablation of the previous TurtleBot cohort.

## Measured result

Exact instruction: `move forward, then go to the trashcan on the right`.

| Measurement | Result |
| --- | --- |
| Navigation run | `runs/navigation01` |
| Consumed model STOP | decision 35 |
| Last in-flight response | decision 36, never enqueued |
| Termination | `model_stop` |
| Terminal target distance | 2.300 m |
| Closest target distance | 2.275 m |
| Terminal dog-bed distance | 1.519 m |
| Minimum base height during navigation | 0.290 m |
| Model/demo service window | 61.04 s, below the 600 s supervisor limit |
| Post-STOP sampled motion | 3.403 s; max forward 0.082 m/s, max yaw 0.055 rad/s, max XY drift 0.034 m |

The quadruped remained upright and the policy received zero velocity after STOP.
The post-STOP figures include physical braking and balance motion; do not label
this as the old TurtleBot's exact-zero stillness pass. The consumed STOP input
has OPOS (245,165) on the dog-bed image region while the green trashcan is visible
to its right. This is visual evidence of a pointing association, not a causal
proof of internal model reasoning.

The inherited WebSocket harness reports `native_stop_seq: 0` because the client
sequence was already reset when its stop snapshot arrived. The authoritative
consumption trace records seq 35. The analysis and film use that trace, not the
reset snapshot sequence.

## Validation and retained failure

- 16/16 contract and physical locomotion smoke checks passed: history/reset,
  quaternion orientation, policy call, action mapping, contact masks, upright
  walking and turning, zero command after stop. Forward displacement 1.380 m;
  turn 1.723 rad; final two-second XY drift 0.00465 m.
- 27/27 upstream demo tests passed. Targeted Ruff checks passed.
- 2,472 source/input hashes matched local to remote before navigation; all
  20 original navigation checkpoint files were rehashed and matched.
- 36/36 request/JPEG/raw-output joins match the official model records.
- 244 camera pairs, index rows, saved states and writer-confirmed frames;
  zero recorded queue drops, write failures, duplicate names or malformed rows.
- Both MP4s fully decode locally. Navigation image and metrics were inspected.
- `locomotion_smoke01` is retained as a failed integration attempt: the original
  robot masks (0/1) could not contact the ProcTHOR floor (8/15), so the robot fell
  through it. The adapter uses 2/13 to enable environment contacts while keeping
  robot self-collision disabled. `locomotion_smoke02` verifies the correction.
- The task model/demo processes exited. Ports 8050/8088 are free. Protected
  Isaac Sim processes 1213/1251 remained running; GPU usage returned to 2,903 MiB.

## Reproduction and source ownership

Local VLA is the source of truth. The runnable copy is
`../work/LightNav-0-lite3-v1`. All source differences from pinned LightNav commit
`d83fbfb9748ca6b497a2f2a7f4a3e95e2110e40c` are in
`patches/lite3_adapter_and_capture.patch`. Lite3 source/assets/policy provenance
is in `setup/import_provenance.json`, `setup/lite3_asset_manifest.json`, and
`policy/policy_manifest.yaml`. The source snapshot was imported from committed
machine-dog files; that repository was not modified.

The remote prefix is
`/home/ubuntu/sun/vla_exec/2026-09-09_lightnav0_official_demo_rented4090`.
`scripts/run_trial.py --exp PREFIX --run UNIQUE_RUN` launches the existing
model/demo interpreters with task-owned source paths and cleans their process
groups. The recorded invocation uses `scripts/run_job.py --seconds 600` around
it. Source verification and the walking smoke gate precede a model launch.

ONNX Runtime is isolated under `PREFIX/work/lite3-v1-python-overlay`; package
versions are in `setup/overlay_requirements.txt`. The existing LightNav and demo
environments were not modified. The failed pip invocation and successful isolated
installation logs are retained. `scripts/compose_trial.py` regenerates the local
film from the returned raw evidence using Pillow and ffmpeg.

No training, physical robot actuation, extra navigation attempts, staging,
commits or pushes were performed.
