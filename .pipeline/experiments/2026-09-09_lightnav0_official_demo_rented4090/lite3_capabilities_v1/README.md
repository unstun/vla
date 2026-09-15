# Lite3 capability probes: distance, local avoidance, and Chinese prompts

Eight independent, single-shot cases executed on rented RTX 4090 on 2026-09-10
UTC. Navigation remained LightNav-0 BF16 with vLLM 0.19.1; walking remained the
user-selected model_149999 FP32 ONNX policy. All eight ended with a consumed
native model STOP. No target-distance rule stopped the robot.

**Measured finding:** none of the four numeric-distance commands stopped within
the predeclared ±0.20 m tolerance. Chinese text was delivered unchanged and
produced motion, but numeric distance accuracy was poor in both languages.
The blocked-route cases did not demonstrate contact-free detouring: English
climbed onto the box and stopped there; Chinese steered toward its side, contacted
and climbed its edge, then got past it.

## Watch

- [All eight tests, 73.35 seconds](media/all_eight_tests.mp4).
- [English blocked route](media/goal_blocked_en/run.mp4).
- [Chinese blocked route](media/goal_blocked_zh/run.mp4).
- [Raw measured table](analysis/summary.csv), [full analysis](analysis/summary.json).

Each individual film preserves the instruction-to-termination wall interval.
The combined film concatenates independent cases; its case clock restarts at each
reset. The camera images are recorded native RGB, upscaled for display. The route
diagram and all distance/obstacle annotations are offline analysis only.

## Distance commands

Primary measurement is signed forward displacement in the body's initial frame,
from the settled instruction-start pose to the final recorded pose. Net
displacement, sampled XY path length, lateral/yaw error and pose at consumed STOP
are also retained. The diagnostic pass requires native STOP, distance error
<=0.20 m, lateral error <=0.25 m, and heading error <=15 degrees.

| Exact prompt | Requested | Forward travel | Signed distance error | Result | Video |
| --- | --- | --- | --- | --- | --- |
| Walk forward 1 meter, then stop. | 1 m | 3.468 m | +2.468 m | fail | [EN 1 m](media/distance_1m_en/run.mp4) |
| 向前走1米，然后停下。 | 1 m | 4.375 m | +3.375 m | fail | [ZH 1 m](media/distance_1m_zh/run.mp4) |
| 向前走2米，然后停下。 | 2 m | 4.162 m | +2.162 m | fail | [ZH 2 m](media/distance_2m_zh/run.mp4) |
| Walk forward 2 meters, then stop. | 2 m | 3.266 m | +1.266 m | fail | [EN 2 m](media/distance_2m_en/run.mp4) |

The bin remained visible in these cases as scene context; it was not named in the
distance instructions. All four ended much closer to the bin than to their
requested stop locations. This association does not prove why the model ignored
the requested distance. These experiments do not isolate numeric understanding
from visual attraction or other closed-loop effects.

## Goal approach and obstacle behavior

English: `Go to the green trashcan, then stop.`

Chinese: `走到绿色垃圾桶旁边，然后停下。`

| Scene / language | Final distance to bin root | Box-contact physics steps | Passed box | Observed behavior |
| --- | --- | --- | --- | --- |
| Clear / EN | 1.022 m | 0 | n/a | approached and stopped short |
| Clear / ZH | 0.807 m | 0 | n/a | approached and stopped short |
| Blocked / EN | 2.338 m | 4,410 | no | climbed onto the box and stopped on it |
| Blocked / ZH | 0.871 m | 1,694 | yes | moved toward the side, contacted/climbed the edge, and passed |

Contact steps count 1 ms physics intervals with an active robot/box contact,
including standing on the box; they are not counts of independent crashes.
Floor contacts are excluded. The largest lateral deviations were 0.088 m (EN)
and 0.533 m (ZH). Neither blocked case passed the box without contact.

The goal-radius diagnostic was fixed at 0.75 m before execution. None of the four
goal-command cases ended inside it; report the raw distances rather than treating
that threshold as an official benchmark success definition. The low box was
physically traversable: getting over it in one run is distinct from avoiding it.

## Setup and limits

- Controlled 10 x 8 m textured arena; same robot/camera/controller as Lite3 v1.
- Actual green-trashcan geometry from the pinned ProcTHOR scene, moved to
  (10.5,13.8) and rotated 90 degrees about world Z to face the robot.
- The two evaluated scenes differ only by a box at (8.25,13.8), size
  0.60 x 0.90 x 0.30 m. There is space to detour on either side.
- Initial robot spawn is (6.5,13.8,0.35); recorded settled start poses are used
  for distance measurements. Model and walking history reset between cases.
- Exact order and prompts are in `cases/suite.json`. Each case had a 40 s active
  wall / 160-decision cap, followed by 3 s of post-STOP observation.
- Total model/demo service window: 138.22 s, below the 720 s budget.
- No training, extra model episodes, prompt rewriting, external avoidance
  planner, odometry-triggered stop, or real-robot actuation was added.

These are one run per condition in a controlled scene. They do not establish a
general English-versus-Chinese ranking, robust obstacle avoidance, or hardware
readiness. A taller non-traversable obstacle would test detouring separately from
climbing. Repeated trials and a furnished-scene follow-up remain untested.

## Evidence checks and source

- 20/20 preflight checks: UTF-8/hash identity, signed body-frame distance,
  paired-scene equality, standing/walking, real overlap detection, and counter reset.
- 27/27 upstream demo tests passed; targeted Ruff checks passed.
- 2,480 source/input hashes matched local to remote before model execution.
- 299/299 request/JPEG/raw-output joins matched official records, including all
  Chinese instructions. The model sample builder uses the session instruction.
- Clear capture: 1,437 pairs; blocked capture: 445 pairs. Index, JPEG and state
  counts agree; no recorded losses or hash mismatches.
- Eight individual MP4s and the combined film fully decode locally. Individual
  presentation duration differs from recorded wall span by less than one 20 fps frame.
- Both task services were stopped; ports 8050/8088 are free. Protected Isaac Sim
  processes 1213/1251 remained running and GPU use returned to 2,903 MiB.

The first static preflight used a 0.8 m box that hid the entire target. Its inputs
and camera images are retained under `runs/preflight01`; it made no LightNav calls.
The box was lowered and the target reoriented before all eight model trials.
`runs/preflight02` is the evaluated scene's preflight.

The local VLA repository is the source of truth. The new work copy is
`../work/LightNav-0-lite3-capabilities-v1`; the parent Lite3 integration remains
unchanged. `patches/capabilities.patch` records the delta from the parent. The
source/input manifests, scene provenance and runtime artifacts are under `setup/`.
The postprocessing script was corrected after execution to leave goal-command
pass fields unset for distance cases; that did not change the experiments or raw data.

Reproduction tools: `scripts/build_scenes.py`, `preflight.py`, `run_suite.py`,
`run_episode.py`, `source_manifest.py`, `analyze.py`, and `render_videos.py`.
Use the existing remote interpreters and ONNX overlay documented in
`../lite3_v1/README.md`; wrap a new authorized suite with `run_job.py --seconds 750`.
Local rendering uses Pillow, ffmpeg and the macOS Arial Unicode font.

Not staged, committed, or pushed.
