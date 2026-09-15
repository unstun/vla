---
origin: ai_execution
date: 2026-09-09
executor: Opus
status: review
request_id: 2026-09-09_zh_between_two_chairs
---

# Execution return: zh_between_two_chairs

## Executed instruction

Verbatim, from `request.json`:

> 往前走，走到两个椅子中间

- `instruction_utf8_sha256`: `b3f47cd62a3b223158a8ad135d295b49a2a50325c0379bc159e60cc68ee7f097`
- `instruction_mode`: verbatim (no translation, no paraphrasing)

### Instruction delivery proof

The annotation stores `往前走，走到两个椅子中间.` (with a period sentinel).
Upstream's `instruction_text[:-1]` slice removes only the period, yielding
`往前走，走到两个椅子中间`. Byte-for-byte UTF-8 equality with
`request.instruction` is confirmed both locally and through the actual
prompt-template substitution path
(`habitat_vln_evaluator.py:438–439`). Verification record:
`instruction_verification.json`.

## Run identity

| Field | Value |
|---|---|
| Run ID | `zh_chairs_v1` |
| Supervisor command | `python3 scripts/run_job.py --seconds 900 zh_chairs_v1 -- bash public_scenes/requests/2026-09-09_zh_between_two_chairs/run_zh_chairs_eval.sh zh_chairs_v1` |
| Evaluator command | `python scripts/eval/eval.py --config public_scenes/configs/habitat_dual_system_zh_chairs_cfg.py` |
| Launch directory | `work/InternNav` |
| Exit code | 0 |
| Timed out | false |
| Wall seconds (supervisor) | 54.207 |
| Episode wall seconds | 35.217 |
| GPU deadline | 900 s (not reached) |
| Evaluator step cap | 500 (not reached; 51 steps) |

## Environment

| Component | Version / value |
|---|---|
| Python | 3.9.23 |
| PyTorch | 2.6.0+cu124 |
| Habitat-Lab | 0.2.4 |
| Habitat-Sim | 0.3.3 |
| Transformers | 4.51.0 |
| Diffusers | 0.32.2 |
| GPU | NVIDIA GeForce RTX 4090 |
| BF16 supported | true |
| CUDA peak memory (run) | 17 766 818 816 bytes (~16.5 GB) |

## Pinned identities

| Asset | SHA-256 |
|---|---|
| Annotation (`zh_between_two_chairs.json.gz`) | `052ac355e19e6d5a4d05eeefc66a78d0696bf705e2706c7fe613fbb832cb95e5` |
| Eval config (`.py`) | `bb5c4f732456048f9bb78c534effc958b9e8aa52ce448f4db9f6d0b2929ea05c` |
| Habitat YAML | `0fc6f45e7f0d5cc581bf11876e2d41b85b620f5aa41c8ed5546577027ee78782` |
| `eval.py` | `95d46250bd99bfb0e78be562185ec1f255a6264b3d2af6c564c15a9fe6a63efc` |
| `habitat_vln_evaluator.py` | `a05268d5e4fac8ab6147d2c828e16ae76d413fe074d2e7f0f99e26ae6fcbf3e7` |
| `vln_utils.py` | `cf51aafbd49b833d0264f09ad4cd4e4bb1b1fc8b9159f2b8fd771237fb6a04ac` |
| `skokloster-castle.glb` | `b14e29e17f5e31d86a1002eefd77b7d345b265006481739ae480a847e6623f56` |
| `skokloster-castle.navmesh` | `1a9a5bd123af8001f0ea2c5c8d326cb3fd39808ca771fc766856af8f0772391d` |

The evaluator hash matches v2–v5 of the existing public-scene runs. No
evaluator code was modified for this request.

## Observed behavior

### S2 prompt sequence (13 calls)

| Step | Branch | Raw output | Interpretation |
|---|---|---|---|
| 0 | level_view | `←←←←` | Turn left 4×15° = 60° |
| 4 | level_view | `←←←←` | Turn left 4×15° = 60° (cumulative 120°) |
| 8 | level_view | `↓` | Look down |
| 8 | look_down_followup | `326 180` | Pixel goal at (326, 180) |
| 17 | level_view | `↓` | Look down (replan after forward budget) |
| 17 | look_down_followup | `348 180` | Pixel goal at (348, 180) |
| 26 | level_view | `↓` | Look down (replan) |
| 26 | look_down_followup | `348 178` | Pixel goal at (348, 178) |
| 35 | level_view | `↓` | Look down (replan) |
| 35 | look_down_followup | `250 238` | Pixel goal shifts left and down |
| 44 | level_view | `↓` | Look down (replan) |
| 44 | look_down_followup | `345 308` | Pixel goal at (345, 308) |
| 50 | level_view | `STOP` | Learned episode STOP |

### S1 trajectory calls (14 calls)

All pixel-goal events used the `look_down_followup` S2 branch.
S1 was invoked 14 times with total inference time 4.058 s.
S2 total inference time was 7.365 s.

### Trajectory

- Start: `[-1.968, 0.200, 12.827]`, rotation `[0.741, 0, -0.672, 0]`
- Terminal: `[-5.088, 0.013, 6.907]`, rotation `[0.952, 0, 0.305, 0]`
- Displacement: ~6.9 m, bearing roughly south-southwest
- Collisions: **0** throughout the episode

### STOP provenance

Five `stop_provenance` events occurred during the episode:

1. Step 16: `forward_budget_exhausted` — pixel goal cleared, S2 replans
2. Step 25: `forward_budget_exhausted` — pixel goal cleared, S2 replans
3. Step 34: `forward_budget_exhausted` — pixel goal cleared, S2 replans
4. Step 43: `forward_budget_exhausted` — pixel goal cleared, S2 replans
5. Step 49: `s1_stop_mid_segment` — S1 output included STOP action, pixel goal cleared

The terminal STOP at step 50 was a **learned S2 STOP** (`is_learned_episode_stop: true`).
The episode did not terminate by step cap, wall deadline, or fallback.

### Visual description

The agent started in the castle room facing a wooden table and paintings.
It turned left 120° to face a corridor with chairs along the walls,
then navigated forward via five pixel-goal segments toward a row of ornate
high-backed chairs with striped upholstery. The terminal first-person view
shows two chairs: a large chair with striped fabric prominently visible
center-right, and a second chair partially visible on the left. The agent
stopped at what appears to be the gap between these two chairs.

**Which chairs the policy selected:** The ornate high-backed chairs with
striped upholstery along the wall beneath the windows in the large hall.
These are the same chairs described in the original episode 1's English
instruction as "high-backed chairs standing between the windows."

**Whether it stopped between them:** The terminal view and the pixel-goal
progression suggest the agent stopped adjacent to the space between two
chairs. Whether it is precisely "between" them requires visual review of
the video.

## Qualitative assessment limitation

No coordinate ground truth for the intended pair of chairs was specified.
The bookkeeping goal in the annotation is set to a navigable point ~1.1 m
from the start position, used solely to satisfy Habitat's dataset schema
and avoid SPL division-by-zero. All coordinate-based metrics
(success, SPL, oracle success, navigation error) are reported below as raw
bookkeeping values; they do not measure task success.

**User-task success: unscored, pending visual review.**

### Raw bookkeeping metrics (not meaningful)

| Metric | Value | Note |
|---|---|---|
| success | 0.0 | Against bookkeeping goal 1.1 m from start |
| spl | 0.0 | Against bookkeeping goal |
| oracle_success | 1.0 | Agent was within 3 m of bookkeeping goal (trivially, at start) |
| navigation_error | 7.165 m | Distance from terminal position to bookkeeping goal |

## Seed / RNG settings

No explicit Torch seed was set. Per the lead review (P2), the evaluator
seeds NumPy but not Torch; the S1 diffusion sampler uses
`randn_tensor(..., generator=None)`, which draws from unseeded Torch RNG.
This single run therefore used default (uncontrolled) random initialization.

## Local video paths

| Video | Path (relative to experiment root) | SHA-256 | Size |
|---|---|---|---|
| First-person (vis_debug) | `public_scenes/runs/zh_chairs_v1/vis_debug/epoch_0/skokloster-castle_0001.mp4` | `cc5ffb284cc2758cabfb4ff3844337555a21d19ce42790ec749efa089532bdd9` | 1 179 424 |
| Composite (RGB + top-down) | `public_scenes/runs/zh_chairs_v1/vis_0/skokloster-castle/0001_success0.mp4` | `6e1d7a46513ba4b50b25580893bd98fdc3349058faf6e6dbbca31a75b41e7973` | 6 821 667 |

Both MP4s decoded fully without errors (ffmpeg decode test and ffprobe frame
count = 51, matching episode steps). The composite video includes a top-down
path view with the actual trajectory (blue) and start marker. The bookkeeping
goal marker (red) is near the start and does not draw an unrelated reference
route.

## Deviations from execution package

1. **Bookkeeping goal position:** The package suggests using bookkeeping-only
   goal fields. Initially set to the start position (goal == start), but
   Habitat-Lab 0.2.4's SPL measurement divides by the live
   `DistanceToGoal` measurement at reset — not the annotation's
   `geodesic_distance` field — producing `ZeroDivisionError`. Resolved by
   using a nearby navigable position (1.1 m from start, the second waypoint
   of the original episode 1 reference path) as the bookkeeping goal. This
   position has no semantic relationship to the instruction and is labeled
   as bookkeeping-only. Two failed runs (`zh_chairs_v1` with goal == start)
   were cleaned up on the remote before the successful run.

2. **Top-down map reference path suppression:** The package requests hiding
   unrelated reference paths/goal markers in the top-down map. Rather than
   modifying the shared evaluator code, the bookkeeping goal was set close
   to the start (~1.1 m), which minimizes the drawn shortest-path line and
   goal marker to a small area near the start. No old green reference route
   appears. The evaluator code is unchanged (hash matches v2–v5).

3. **Lossless inference inputs:** The package notes "Preserve lossless
   inference inputs where practical." Goal-frame PNGs (10 files: model
   input and saved raw view for each of the 5 pixel-goal events) and the
   starting RGB are preserved. Full lossless per-step RGB/depth arrays are
   not saved; this matches the P3 scope note in the lead review.

## Sync status

All run artifacts were pulled from
`ubuntu@117.50.179.202:/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090`
to the local experiment directory via rsync. Annotation hash verified
matching between local, remote, and `inputs.json`. Evaluator hash matches
v2–v5 runs. Videos decoded cleanly on local.

The task remains at `review` pending lead acceptance. Nothing was staged or
committed.
