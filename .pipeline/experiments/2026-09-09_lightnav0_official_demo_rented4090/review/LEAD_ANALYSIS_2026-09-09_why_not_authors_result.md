---
origin: ai+local_inspection+official_upstream
reviewed: false
date: 2026-09-09
author: Claude Fable 5.1 (lead)
scope: why round-1 runs stopped at the dog bed while the authors' demo recording reaches the trashcan
evidence_label: analysis of recorded runs; no new inference was executed
---

# Why the reproduction did not match the authors' demo recording

"The authors' reported result" for this case is a single recording,
`docs/assets/mujoco_demo.gif` in the pinned repository (87 frames at 10 fps, showing the
demo web page). The demo README makes no success-rate claim. The paper's benchmark
numbers are Habitat evaluations (0.88 m camera, 120° field of view, 4 fps history) and
are not what this demo measures; a single-case failure here says nothing about them.

## 1. The setup matches the recording (verified)

| Item | Authors' recording | Our runs | Evidence |
|---|---|---|---|
| Instruction | `move forward, then go to the trashcan on the right` | identical | GIF text box; `runs/case.json` |
| Start view | spawn (6.5, 13.8, 0) | identical; first frames differ by 7.8 / 255 mean absolute pixel difference (GIF palette noise, edges only) | `review/lead_start_frame_compare.png` |
| Renderer / camera | 480x270, 18.8-18.9 Hz camera | 480x270, 19.0 Hz | GIF metrics bar; snapshots |
| Model latency | 107-325 ms per step | 114-306 ms, mean 150-167 ms | GIF metrics bar; `actions.json` |
| Controller | "MPC tracking the VLN path · 2.8 ms" in the GIF status line | same MPC, solve 8-10 ms | GIF frames 43-76; snapshots `mpc.solve_ms` |
| Checkpoint | public weights have one release (2026-08-31); later HF commits touch only the model card | same release, hash-verified | HF commit list, fetched 2026-09-09 |
| Episode length | 8.6 s simulated (58.9 s to 67.5 s) | 9.2-10.3 s simulated | GIF; snapshots |
| Outcome | stops about 1 m in front of the green trashcan, `OPOS · point` on it | stops 0.9-1.1 m in front of the gray dog bed, 2.3-2.6 m from the trashcan | GIF last frame; `review/lead_terminal_geometry.json` |

The unused legacy controller `mujoco_demo/vln_mujoco/control.py` is referenced only by
its unit test, so the recording and our runs used the same MPC.

## 2. Where the two diverge: the first second

Authors (`review/lead_authors_gif_first_1p5s.png`): the first prediction places the
affordance point (`APOS`) right of center at the far doorway, and the robot turns right
immediately and continuously. The window slides from the image center to the left edge
between 0.3 s and 1.0 s after the first prediction, about 37° of yaw, and is out of view
by 1.2 s. By 2.3 s the robot faces into the next room with the trashcan ahead-right and
the dog bed on its left (GIF frame 32-43); the object pointer (`OPOS`) then locks onto the
trashcan and stays there until the stop.

Ours (`actions.json`, snapshots on the simulated clock):

| Simulated time after start | rep_01 yaw | rep_02 yaw | rep_03 yaw |
|---|---|---|---|
| 1.0 s | 0° | -9° | -9° |
| 2.0 s | -5° | -19° | -30° |
| 3.0 s | -40° | -48° | -35° |

The first prediction is the same as the authors' (same `apos` cell, px (325, 145), a
chunk turning 30° right). From the second prediction on, the model alternates: chunks
at 0.4-1.6 s are mostly straight (final yaw -3° to -22°, `apos` at the image center
(315, 145)) with isolated right-turn chunks (final yaw -42° to -51°). Only 5 / 3 / 2 of
the first twelve chunks turn more than 25°. The MPC, which replans every 0.1 s on the
latest chunk and weights position ten times more than yaw, realizes the majority and
drives nearly straight for the first 1.5-2 m. The right turn therefore happens 1-2 s
later and 1-1.5 m further along than in the recording, so the robot enters the room on a
line where the dog bed is central and the trashcan sits at the right edge of the image.

## 3. Then the grounding fails and the stop follows the wrong object

Projecting the scene's `ashcan` (8.52, 9.36) and `pad` (9.82, 10.41) bodies into each
model input frame with the compiled camera (112.2° field of view, 0.198 m height) and
comparing with the model's object pointer (`review/lead_terminal_geometry.json`, section
"projection" in the lead's notes):

| Run | Trashcan first inside the image | `opos` emissions | within 40 px of the trashcan | within 40 px of the dog bed |
|---|---|---|---|---|
| rep_01 | step 16 | 20 | 0 | 14 |
| rep_02 | step 19 | 24 | 0 | 20 |
| rep_03 | step 15 | 11 | 0 | 10 |

In rep_02 and rep_03 the object pointer settles on the dog bed at steps 11-14, while the
trashcan is still outside the field of view to the right. Once locked, it never moves to
the trashcan even when both objects are visible (rep_01 steps 22-40, the trashcan at
px x 376-454, the pointer at x 245-305). The stop token is emitted when the pointed
object is about 1 m ahead (rep_01: 1.0 m from the pad), which is the learned arrival
behavior applied to the wrong object. In rep_03 the pointer was lost (`opos` not visible
for the last 20 steps) and the model still stopped 0.9 m from the dog bed.

Two observed model-side details make this fragile:

- the two output channels disagree early: at steps 3-5 the affordance point says
  "17° right of center" while the RVQ action chunk says "straight 1.5 m";
- decoding is greedy (temperature 0), so near-tie choices flip with small input
  differences rather than averaging out. The only inputs that differ between runs are
  the capture times of frames while the robot moves, and all three of our runs fell on
  the same side of the early tie.

## 4. What this does and does not establish

- Established: with the pinned code, checkpoint, scene, instruction and controller, the
  outcome depends on an early turn-versus-straight decision that the recording resolved
  one way and our three runs the other way; the later failure is a target-grounding
  error (dog bed taken for the trashcan) followed by a correctly formed stop.
- Not established: the success rate of this case. The recording is one run with no
  stated selection; our sample is three runs, all failures. Neither side supports a
  rate.
- Not a cause: renderer, instruction, spawn, latency, controller, checkpoint revision
  or history timing differences. All were checked above. GitHub issues on the
  repository (two, unrelated) contain no report on the demo.
- Not testable here: whether the vLLM in-process backend and the `hf` backend produce
  the same greedy tokens at the tie steps. The upstream patch binds vLLM private APIs
  and bf16 kernels differ, so the recording may have been produced with different
  numerics. This is the one remaining setup difference that could not be excluded.

## 5. Cheapest next experiments (require Dr Sun's authorization)

Decision 2026-09-09 (Dr Sun): stay on the official default, the in-process vLLM
backend in BF16 as the repository prescribes. Items 1 and 3 below (Transformers
backend comparisons) are declined and must not be re-proposed as part of this task;
item 2 remains the candidate follow-up after the correction round.

1. Offline replay: feed the recorded model inputs `records/.../image_000001..jpg`
   through `lightnav-predict --frames` with `--backend vllm_local` and `--backend hf`
   at the same settings, and compare tokens step by step with `actions.json`. This
   tests vLLM determinism and backend sensitivity at the tie steps without any
   simulation. Cost: minutes of GPU time.
2. Ten more closed-loop repetitions (same case) to estimate an outcome rate instead
   of arguing from three runs, keeping the fixed recorder from the correction round.
3. Three closed-loop repetitions with `--backend hf` (the documented fallback) to see
   whether the early turn is sustained under the other numerics.
4. Only after those: a paired instruction variant (for example naming the "green
   trashcan") as an explicitly labeled prompt sensitivity trial, never as a
   replacement for the official case.
