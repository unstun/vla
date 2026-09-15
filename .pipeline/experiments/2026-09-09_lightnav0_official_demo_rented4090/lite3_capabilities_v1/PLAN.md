# Lite3 local avoidance, metric distance, and Chinese prompt probes

Stage: experiment + analysis. Dr Sun requested these three capabilities after
the initial Lite3 integration. This authorizes the bounded simulated tests below.
Keep navigation LightNav-0 BF16 revision
`826dc5fbfa37afa8293d2e336d329b6ffc0bfb64`, vLLM 0.19.1, the user-selected
model_149999 FP32 walking policy, controller settings, camera and robot dynamics.

## Change boundary

The existing harness can send only one English trashcan instruction in the
furnished scene. This task adds task-file UTF-8 instructions, controlled clear
and blocked scenes, and obstacle-contact telemetry at every physical substep.
Changes live in this package and the separate `work/LightNav-0-lite3-capabilities-v1`
copy. Preserve all earlier runs and source snapshots. No model/policy tuning,
training, hardware actuation, distance-triggered stopping, external planner,
language translation, obstacle coordinates in the model input, or retries for
better results are included.

## Frozen cases and scene

`cases/suite.json` fixes eight single-shot cases and their order: 1 m EN/ZH,
2 m ZH/EN, then green-trashcan EN/ZH without and with a blocking box. The
English and Chinese prompts preserve the same requested motion and STOP.
All language text is transmitted verbatim and hashed in the official records.
These are diagnostic comparisons, not statistical estimates of language effects.

Use a 10 x 8 m textured arena centered on the existing spawn (6.5,13.8), with
the actual green trashcan object copied from the pinned ProcTHOR scene at
(10.5,13.8). The blocking box is centered at (8.25,13.8), half-extents
(0.30,0.45,0.15), with free detour space on both sides. The bin is rotated 90 degrees about world Z to present its front. The two scene files
differ only by the box body. This is a new controlled test scene, not the
official demo or a full obstacle-avoidance benchmark.

## Measurements and predeclared checks

- Distance: forward displacement in the initial body frame, lateral error,
  net displacement, XY path length, yaw error, consumed model STOP, and settling.
  A diagnostic pass requires native STOP, absolute forward error <=0.20 m,
  lateral error <=0.25 m, and yaw error <=15 degrees. Report raw errors regardless.
- Avoidance: record all active robot/box contacts at the 1 ms physics rate,
  with force and penetration observations. Measure whether the robot passes
  beyond the box, lateral detour and goal approach. Passing the box without
  contact and reaching/stopping within 0.75 m of the target are separate fields.
  A stopped or stuck robot that never passes the obstacle is not avoidance success.
- Chinese: compare the same two scene geometries and requested distances with
  English. Valid parsing alone is not instruction-following success.
- Ground-truth geometry is analysis-only. The model receives its native RGB
  history and exact instruction through the unchanged upstream protocol.

Reset locomotion and model history between cases; retain settled initial poses.
Keep the model resident while running the eight cases serially. Each case has
40 s active wall time / 160 decisions plus 3 s post-STOP observation; each
harness process is bounded to 55 s. Bound the complete service window to 720 s
and the outer supervisor to 750 s. Stop on falls, recorder errors or controller
errors with explicit labels; preserve contact events and all failures.

## Execution and return gate

1. Unit-check UTF-8 round trips, signed forward/lateral projection, test-file
   identity, contact detection and reset counters. Compile/render both scenes,
   confirm visible bin and obstacle, and run short model-disconnected checks.
2. Verify local/remote source and input hashes. Reuse the already verified
   checkpoint, Lite3 assets, ONNX overlay and existing interpreters.
3. Run exactly the frozen eight cases; do not replace failed attempts.
4. Return every case's original JPEGs, state/contact traces, official model
   records, measured metrics and locally decoded video. Publish a comparison
   table with the exact prompts and limitations.

Local VLA is the sole source of truth. Remote execution prefix remains
`/home/ubuntu/sun/vla_exec/2026-09-09_lightnav0_official_demo_rented4090` on
`rented4090`. Pin the parent source using `../lite3_v1/setup/source_manifest_navigation01.json`.
Record every new difference as a patch and source manifest. Return and hash-check
all raw evidence. Clean only owned process groups; protect Isaac Sim workloads.
