# Journal - sun (Part 1)

> AI development session journal
> Started: 2026-08-16

---



## Session 1: Archive and audit Lite3 VLA survey

**Date**: 2026-08-16
**Task**: Archive and audit Lite3 VLA survey
**Branch**: `main`

### Summary

Archived the referenced survey conversation, verified both package hashes and archive safety, stored 24 paper PDFs as local-only artifacts with a tracked manifest, merged 24 paper and 21 repository records at surveyed status, rechecked the Top 5 from official sources, and preserved the no-import/no-runtime boundary.

### Git Commits

| Hash | Message |
|------|---------|
| `3f782c982e5758d2800e5b6addd1efbf3c0e83a5` | (see git log) |

### Status

[OK] **Completed**


## Session 2: Migrate VLA repository into phdproject

**Date**: 2026-08-18
**Task**: Migrate VLA repository into phdproject
**Branch**: `main`

### Summary

Moved the complete VLA repository to /Users/sun/tongbu/study/phdproject/vla without an old-path symlink; preserved Git, nested Vendor state, research evidence, and relative links; updated live path declarations and passed full harness validation.

### Git Commits

| Hash | Message |
|------|---------|
| `f5f9f8f` | (see git log) |

### Status

[OK] **Completed**


## Session 3: OmniVLA offline reproduction — pinned import and edge smoke

**Date**: 2026-08-18
**Task**: `08-18-omnivla-offline-smoke`
**Branch**: `main`

### Summary

Imported OmniVLA at pinned commit `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68` as a
byte-identical snapshot with a SHA-256 manifest, recorded checkpoint provenance for
`omnivla-edge` (downloaded, hash-verified) and `omnivla-original` (manifest only),
relocated the CLIP ViT-B/32 weights into the project, built an isolated conda env in
which all official pins installed exactly, and ran the official
`inference/run_omnivla_edge.py` eight times on CPU. Two upstream blockers were found
and fixed by patch against a working copy, never the snapshot: `pyproject.toml` is
invalid TOML (blocks `pip install -e .` on every platform) and `Tensor.get_device()`
returns `-1` on CPU. Outputs are shape `(8, 4)`, finite, deterministic across
identical configurations, and match the authors' shipped reference figure visually
(mean absolute pixel difference 0.0208/255, differences confined to the trajectory
curve). The 8B probe stopped at a pre-declared 22 GB memory guard.

### Evidence

- `.pipeline/experiments/2026-08-18_omnivla_offline_smoke/README.md`
- `.pipeline/experiments/2026-08-18_omnivla_offline_smoke/decision_log.md`
- `third_party/2026-08-18_omnivla_5182600/PROVENANCE.md`

### Labels

`imported` for the source and all checkpoint identities; `reproduced` for
OmniVLA-edge only, with the caveat "macOS arm64 / CPU / float32 / no FlashAttention /
patches 0001-0005, not the official CUDA environment"; `omnivla-original` remains
manifest-level `imported` with no forward pass. Nothing `integrated` or `validated`,
and no Lite3 claim.

### Next Gate

Dr Sun reviews the evidence bundle and patch series; a GPU host must be designated
before the official 8B reproduction, and the Lite3 input/action contract remains
undefined.

### Git Commits

| Hash | Message |
|------|---------|
| — | not committed by the executing sub-agent; review and commit belong to the primary session |

### Status

[OK] **Completed** (implementation and follow-ups; awaiting review)


## Session 3: TIC-VLA RTX 5070 Ti hospital compatibility trial

**Date**: 2026-09-08
**Task**: TIC-VLA RTX 5070 Ti hospital compatibility trial
**Branch**: `main`

### Summary

Completed the user-authorized Nova Carter hospital closed-loop trial on gpu5070ti. Recorded one successful episode, retained earlier stalled attempts, synchronized and verified source/model/media artifacts locally, and left the task in review.

### Main Changes

- Added bounded runner, source/config manifests, renderer compatibility patch, resumable verified acquisition, videos and result report.

### Git Commits

(No commits - planning session)

### Testing

- [OK] 184/184 finite (1,30,2) trajectories; 184 nonzero model controls; benchmark success at 1.484381 m with 1.5 m threshold; 86 local integrity checks passed; both videos fully decoded; downloader regression passed.

### Status

[OK] **Completed**

### Next Steps

- Human review of videos and compatibility limits before any additional scene or robot task. Git changes remain uncommitted.


## Session 4: Local speech to simulator video; live UI cancelled

**Date**: 2026-09-08
**Task**: Local speech to simulator video; live UI cancelled
**Branch**: `main`

### Summary

User removed the website and real-time requirement. Added native Mac microphone/existing-audio entrypoint, local pinned SenseVoice ASR, detached bounded offline simulator execution and automatic hashed video download. Synthetic Mandarin audio run 20260908T145239Z_a4b70f reached the evaluator goal with 189 finite trajectories; 29.8-second annotated video and raw frames returned locally with 247 integrity checks. Initial offline divergence retained as failed diagnostic. Live UI/tunnel/browser sessions stopped. Actual human microphone recording remains untested; no Git commit.

### Git Commits

(No commits - planning session)

### Status

[OK] **Completed**


## Session 5: Top-down simulator trajectory video

**Date**: 2026-09-08
**Task**: Top-down simulator trajectory video
**Branch**: `main`

### Summary

Added optional --view top_down to the offline voice/video chain. A fixed output-only orthographic camera provides a ceiling-clipped view of the real hospital scene while preserving the model-facing camera. New run 20260908T150231Z_f402d9 reached evaluator threshold, produced 185 finite trajectories and a 30.52-second 1280x720 video. Fixed projection across 225 samples, video decode/visual QA and 243 local checks passed. Previous videos preserved; no Git commit.

### Git Commits

(No commits - planning session)

### Status

[OK] **Completed**


## Session 6: Direct Chinese instruction propagation and failed navigation trial

**Date**: 2026-09-08
**Task**: Direct Chinese instruction propagation and failed navigation trial
**Branch**: `main`

### Summary

Removed fixed English substitution from the demo parser and added direct text input. UTF-8 runtime request is copied as a file; per-run scenario, environment, behavior and every model audit preserve the original instruction. Four targeted tests passed. Run 20260908T151850Z_e8fd96 sent 走到自动售货机前 unchanged in all 461 model calls, but failed the 70-second scenario with 15.0642 m error and physical collision detected. Actual 102.16-second overhead video, logs and raw frames are local with 723 checks. This validates propagation only, not Chinese navigation success; no fallback translation or Git commit.

### Git Commits

(No commits - planning session)

### Status

[OK] **Completed**


## Session 7: Matched full Chinese-English navigation pair

**Date**: 2026-09-08
**Task**: Matched full Chinese-English navigation pair
**Branch**: `main`

### Summary

Predeclared full semantically matched instructions and fixed scene/inference seed 36. Added optional validated inference seeding while preserving verbatim input. Two fresh sequential runs used the same source manifest and matching non-language scenario: Chinese 20260908T153532Z_615007 failed with 19.0298 m final error and reported collision; English 20260908T153918Z_f89862 reached the 1.5 m evaluation radius with 1.4946 m error and no reported physical collision. Both initial front views contained the vending machine. Two videos, raw frames and 969 artifact checks plus four front hashes are local. Both simulator groups exited. One exploratory pair; no distance/occlusion manipulation or causal language claim. No Git commit.

### Git Commits

(No commits - planning session)

### Status

[OK] **Completed**


## Session 8: Frozen-input TIC-VLA language and controller diagnosis

**Date**: 2026-09-08
**Task**: Frozen-input TIC-VLA language and controller diagnosis
**Branch**: `main`

### Summary

Executed 16 frozen first-call predictions and 8 fixed-input cache interventions on RTX 5070 Ti. Original Chinese/English first trajectories reproduced exactly; repeats and seeds 36-38 agree. Language-conditioned trajectory differences persist on both RGB fixtures and follow the exchanged cache. Source controller parity explains strong right-turn requests from near-origin Chinese plans. 97 source/asset checks, 11 successful and 6 failed-attempt artifact checks passed locally. No simulator/model behavior change, neural root-cause claim or navigation fix. Task remains review; no Git commit.

### Git Commits

(No commits - planning session)

### Testing

- [OK] Real-model output parity, repeat equality, fixed-input cache donor parity, source-derived controller parity and local SHA-256 checks passed.

### Status

[OK] **Completed**

### Next Steps

- Review diagnostic evidence before a target-phrase or near-origin controller intervention; validate any future fix in closed loop.


## Session 9: Chinese three-meter stop simulation: failed instruction following

**Date**: 2026-09-08
**Task**: Chinese three-meter stop simulation: failed instruction following
**Branch**: `main`

### Summary

Created an isolated copy of the pinned demo for the exact Chinese command 向前直走 3 米，然后停下. Disabled benchmark goal termination and automatic backup; added observation-only displacement, path, speed and timeline logging. First child crashed with SIGSEGV during periodic traceback dumping; preserved its 333 checked artifacts and source. Retry disabled that diagnostic dump only and completed 1020 frames with 301 finite predictions. Maximum forward progress 0.106 m, final forward -8.440 m, sampled path 9.771 m, zero qualifying near-target stops. At cumulative path 3.009 m speed remained 1.382 m/s. Completed 49.24-second overhead video and 363 verified artifacts are local. Timeline after command was 15 s, versus 30 frame-derived seconds. No model/controller fix or Git commit.

### Git Commits

(No commits - planning session)

### Testing

- [OK] Eight unit tests, unchanged policy/controller checks, 71 source and 21 asset checks, both videos decoded, completed run and local raw-frame hashes verified.

### Status

[OK] **Completed**

### Next Steps

- Review failed metric-language result; further prompts or controller changes require separate, explicitly labeled comparisons.


## Session 10: Matched Chinese-English three-meter stop comparison

**Date**: 2026-09-08
**Task**: Matched Chinese-English three-meter stop comparison
**Branch**: `main`

### Summary

Ran a fresh Chinese-English pair under one shared 78-file source manifest, identical non-language configuration and seeds 36. Both completed 301 predictions and failed sustained stopping near 3 m. Chinese passed the reference at 1.382 m/s and continued to 20.208 m sampled path; English turned away and traveled 9.610 m. All 726 run artifact hashes and two initial RGB hashes passed locally after retried Chinese download. Original videos plus a 15.05-second simulator-time-aligned side-by-side video and full trajectory plot are local. Initial RGB mean absolute difference 1.044/255; large same-language variation versus prior Chinese trial limits causal/ranking claims. Model, behavior and controller source remained unchanged. No Git commit.

### Git Commits

(No commits - planning session)

### Testing

- [OK] Nine targeted tests; 78 source and 21 model-asset checks; 602 exact instruction audits; identical non-language configs/camera/timelines; both originals and comparison decoded and visually inspected.

### Status

[OK] **Completed**

### Next Steps

- Review comparison; isolate same-language variation or metric-stop representation before making language capability claims.


## Session 11: LightNav-0 BF16 on 5070 Ti and Trellis 0.6.15 update

**Date**: 2026-09-09
**Task**: LightNav-0 BF16 on 5070 Ti and Trellis 0.6.15 update
**Branch**: `main`

### Summary

Nine replay predictions passed on RTX 5070 Ti using original BF16; 12.3502 GiB sampled total GPU peak; all 48 returned files verified. Trellis templates updated to 0.6.15 with local configurations preserved. No FP8, simulator or robot run.

### Main Changes

- Added isolated LightNav inference scripts, fixtures, manifests, raw logs and result.

### Git Commits

(No commits - planning session)

### Testing

- [OK] Nine finite 10x3 predictions; identical-input token equality; full source/checkpoint/return SHA-256 gates; range-resume test; Python/shell syntax.
- [OK] Trellis version/current-task checks and 147 protected-file hashes passed at update.

### Status

[OK] **Completed**

### Next Steps

- Human review of the scoped inference report; concurrent work and all changes remain uncommitted.


## Session 12: Prepare LightNav-0 visual reproduction package v3

**Date**: 2026-09-09
**Task**: Prepare LightNav-0 visual reproduction package v3
**Branch**: `main`

### Summary

Prepared a researched manual Opus continuation for rented4090: exact frame/state/request joins, offline overhead rendering, three fixed vLLM BF16 runs, multi-view MP4s and separate stop/arrival assessment. No Opus dispatch or new policy episode.

### Main Changes

- Added continuation_v3 execution package, visual contract, research, static probes, frozen legacy manifest and verified ZIP.

### Git Commits

(No commits - planning session)

### Testing

- [OK] Rehashed 20 remote checkpoint files; inspected 2449 matching source files plus demo uv.lock drift; static state restoration/native-view preservation and actual GL orthographic projection passed on attempt 02.
- [OK] 23 package inputs, 559 unchanged legacy files, relative links, Python syntax, Markdown fences, ZIP content hashes and git diff whitespace check passed.

### Status

[OK] **Completed**

### Next Steps

- Dr Sun manually dispatches the v3 package to Opus; lead reviews real capture/state joins, all videos, stop/arrival traces and returned hashes.

## Session 13: InternVLA-N1 camera-height ablation planning and package

**Date**: 2026-09-10
**Task**: 09-10-internvla-n1-camera-ablation-sim (child of 09-10-lite3-camera-height-internvla-n1)
**Branch**: `main`

### Summary

Answered two questions with local evidence: InternVLA-N1 has only run as an official evaluator on custom public castle episodes (3/5, 2/5), never as an R2R reproduction; the Lite3 sensor-rig camera is 0.42 m high, 0.25 m forward, 20 degrees down versus the 1.25 m level Habitat camera. Dr Sun chose simulation first, then real robot. Created the parent/child Trellis tasks, planning artifacts, four camera-condition YAMLs, derived eval config, per-condition preflight, launcher, matrix runner, summariser, terminology rows, and the Opus execution package (prepared_not_dispatched).

### Main Changes

- `.trellis/tasks/09-10-lite3-camera-height-internvla-n1/prd.md` (parent) and child `prd.md`, `design.md`, `implement.md`, `research/camera-geometry-and-evaluator-protocol.md`, jsonl manifests.
- `.pipeline/experiments/2026-09-08_dualvln_rented4090/public_scenes/requests/2026-09-10_lite3_camera_ablation/**` and `public_scenes/configs/{vln_cam_*.yaml,habitat_dual_system_cam_cfg.py}`.
- `.pipeline/terminology/terminology.md`: camera condition, rig-faithful condition, public-scene functional test.
- Hot zone: status brief, recent changes, open decisions.

### Git Commits

(No commits; awaiting Dr Sun's review of the staged path list.)

### Testing

- [OK] YAML parse (4), py_compile, bash -n, cfg refuses a bad CAM_YAML, summariser reproduces baseline 3/5 and 2/5, authored-file hashes verified with shasum -c.
- [--] Preflight and matrix cannot run locally (no Habitat); they run on rented4090 after manual dispatch.
- [OK] trellis-check pass: 8 defects fixed (z-depth floor expectation, GPU budget measured after closing the preflight simulator, ffprobe frame rule, manifest ordering, preflight dir, crashed-run reporting, SC2164, formula text); provenance regenerated, 15 hashes OK.
- Deviation: implementation was done inline by the lead instead of a trellis-implement sub-agent, to keep the verified context; a trellis-check sub-agent reviewed the files afterwards.

### Status

[OK] **Completed** (commit pending Dr Sun's review): three executor rounds, 20/20 runs returned and verified (manifest 1,571 files); lead review and mount recommendation written; two preflight criteria revised with evidence (navmesh floor gap 0.16 m, quaternion re-normalisation on zero tilt).

### Next Steps

- Dr Sun reviews the lead review; commit the task-owned paths after reviewing the staged list; decide on the confirmatory fixed-camera sim pair (C5/C6, 10 runs, new authorization) before creating the real-robot child.

## Session 13b (2026-09-10): Lite3 second camera and round 4 of the camera ablation

### What was done

- Answered Dr Sun's questions on InternVLA-N1 inputs/outputs from the pinned source (System 1 `nextdit_async` reads no depth; pose and intrinsics unused).
- Established from local manuals that the Lite3 has a built-in wide-angle head camera streamed by the motion host (RTSP :8554/test, H.264 1280x720); four web-search subagents verified D435i/D455 colour FOV from the RealSense datasheet, found a third-party calibration of the head camera (HFOV ~103 deg, ~0.40 m, ~15 deg down), no URDF that models it, and no paper that uses it. Evidence and SHA-256 under `.pipeline/survey/2026-09-10_lite3_cameras_web_sources/` (77 MB, 52 files; 50 MB brochure PDF awaiting a keep/ignore decision).
- Vendor torso mesh brackets the head camera at <=0.28 m ahead and 0.33-0.40 m high; pitch not readable from the mesh.
- Dr Sun kept the head camera and authorized the simulation pair. Added C5/C6 (0.40 m, 0.27 m, level / 15 deg down, HFOV 79, tilt 0) to the request; Opus executor ran 10 runs (all exit 0). Verified: manifest 2,211 OK, inputs hashes match baseline, summary recomputed identically, frames inspected. C5 2/10, C6 5/10 (ep1 5/5); ep2 is a late-stop failure across wide-FOV conditions (oracle success 5/5).
- Round-4 addendum in `review/LEAD_REVIEW.md`, `RESULT.md`; request/package `executed_lead_accepted`; parent PRD, hot zone, spec lesson (report oracle success), memory updated.

### Status

[OK] Round 4 completed and accepted; 30/30 authorized runs used. Commit still pending Dr Sun's review of the staged path list.

### Next Steps

- Dr Sun: authorize the camera-only on-robot measurement; decide on the 50 MB brochure PDF; review staged paths and commit; then create the real-robot child with the measured geometry.

## Session 13c — 2026-09-11 (UTC 04:45–05:50): Lite3 head camera measured on the robot

- Dr Sun asked "can u ssh lite3". Mac was on the robot Wi-Fi; `ysc@192.168.2.1` (motion host RK3588) and the Xavier via jump answered; Orin down. All read-only; no actuation.
- Identified the head camera (UVC 1bcf:2cc8 Sunplus "LRCP F1080P", MJPEG, 1080p/720p/960p modes) and pulled the RTSP stream from the Mac. First frame + level IMU + folded knees showed the horizon far below the image centre: camera points UP.
- Dr Sun supplied an A4 checkerboard (11x8, 20 mm). Wrote `capture_head_cam.sh`, `burst_head_cam.sh`, `calibrate_head_cam.py` (sign verified on synthetic ±20° cases and a flat-board case). First 120 s burst was static (message timing); second burst on his "go" gave 36 poses, RMS 0.29 px: fx 490 / fy 487, HFOV 105 / VFOV 73.
- Upright sheet on a box face: +15.1° (0.27 m) and +16.7° (0.73 m) up. Flat sheet on the floor undetectable (foreshortening, predicted by synthetic test). Adopted +16 ± 2° up.
- Implication written in research doc 6f/6g and notes: bottom edge only 21° below horizontal; no crop reaches even a level evaluation camera; C5/C6 are proxies, not the stock mount. Hot zone, memory updated. Open: mount decision (wide module/D455 on the 20° carrier + sim C7), optional box-flip check, 17 MB evidence dir keep/ignore, commit.
- Lesson: synchronise "go" before a timed capture; test detector feasibility on synthetic foreshortening before asking for a placement.

## Session 13d — 2026-09-11 (UTC 05:55–07:30): round-5 fused-camera simulation prepared

- Dr Sun asked whether the two cameras can be fused into one RGB image, then "Simulate the fused camera first".
- Coverage analysis: level virtual eval camera fully covered in height (head to −22°, D435i to −41°); 15°-down not coverable.
- Built `fused_camera.py` (+ exact synthetic self-test, PASSED), habitat-lab 0.2.4 plugin (three sim sensors + task sensor uuid rgb),
  fused run config importing the plugin (eval.py executes the cfg before Evaluator.init), c7/c8 YAMLs via `make_fused_yamls.py`,
  `preflight_fused.py` (9 stages incl. bit-identical offline recompute and sensor-state checks), round-5 drivers, package/request.
- API facts verified from the v0.2.4 tag (web subagent) and archived under `.pipeline/survey/2026-09-11_habitat_lab_024_sensor_api/`.
- Blocked on dispatch: rented4090 SSH banner timeout from this Mac (TCP connects; gpu40901 reachable). Static check agent pending.
- Round 5 returned (executor ~44 min): c7 0/10, ep1 oracle 0 (one deterministic System-2 route to nearer chairs), ep2 late stops;
  manifest 2524 OK; lead review addendum written. c8 blocked by my own 200 ms cost bound -> 300 ms, round 5b dispatched.
- Pitfall: the executor's return rsync of REQ/ overwrote lead edits made during the run (bound + 5b section); re-applied. Rule:
  no lead edits under REQ/ while a round is in flight, or exclude lead-owned files from the return.

- Round 5b: executor stopped mid-round (idle on its own monitor; stopped it); lead monitored the driver, ran summaries on the remote,
  ffprobe locally (no ffprobe on the remote), regenerated the manifest, rsynced back. c8 2/10 = c5; ep1 oracle 5/5 vs c7 0/5.
  Fusion conclusion: level-camera performance at best; downward view not reachable. 40/40 runs used. Docs/hot zone updated.

## Session 13e — 2026-09-11 (PDT 09:20–09:45): route decision and two corrections

- Dr Sun chose the software-only fusion route (C8 geometry, D435i colour 1280x720, no hardware change).
- Re-read `condition_summary.json` before recording it and found two of my own round-5b statements wrong:
  1. "c8 equals c5" conflated success with oracle success. By runs entering the success radius, C8 is 10/10 (tied with C6,
     above the baseline's 8/10) and C5 is 6/10. Every C8 failure is a late stop. The route's bottleneck is STOP arbitration.
  2. "Fusion cannot reach a downward view" was only true for a full 15 deg. The virtual camera's pitch is free within the
     covered band (-41.1..+52.9 deg); `Cam`/`head_lut`/`warp_d435`/`fuse` are all pose-general and only a guard in the plugin
     forces level. Swept on the self-test render (which reproduces C8's 1.2-1.3 pct at 0 deg): uncovered 1.28 / 2.08 / 3.05 /
     8.78 / 14.56 pct at 0 / 5 / 9 / 12 / 15 deg down; floor first visible 0.65 / 0.54 / 0.46 / 0.42 / 0.38 m ahead.
- Diagnosed the extra 1.8 points at 9 deg: forward-splat gaps, not geometric shortfall (depth 0.6-3.67 m, `depth_valid_max`
  irrelevant, no row over 50 pct empty, extra 3x3 fill passes at cnt>=5 close none and cnt>=3 only reaches 2.33 pct).
  Root fix is a backward warp, which is a real change needing AC10 re-validation.
- Wrote research section 6k (decision, corrections, the seven real-robot deployment gaps, proposed C9), RESULT.md decision
  section, hot zone (both files), memory.
- Robot not reachable this session (Mac on 192.168.31.42, not the robot AP), so the D435i-to-head extrinsic calibration and
  the D435i stream check are deferred; neither blocks C9, which is pure simulation.
- Lesson: report oracle success and success as a pair every time. Collapsing them cost a wrong route summary that stood for a
  full turn, and the corrected reading makes the chosen route look materially better than I had described it.

## Session 13f — 2026-09-11 (PDT ~12:00–13:30): round 6, C9 fused camera 9 deg down = 1/10

- Dr Sun: "Run C9 with the virtual camera 9° down." Built the condition, dispatched, ran, verified, wrote up. 45/45 runs used.
- Two defects found before writing code: the plugin's level-only guard (expected), and `preflight_fused.py` using the
  level-only flat-floor formula `h/tan θ` where `preflight_cam.py` has carried the general `h/(sin p + tan θ cos p)` since
  round 1. At 9 deg the level form reports the implied floor gap as 0.046 m instead of 0.160 m — inside the accepted band,
  so it would have passed silently. Confirmed in Habitat: measured gap 0.1576 m with the corrected form.
- Static review (trellis-check) found two more I had missed: stale `authored_files.sha256`/`provenance.json` (the sync gate
  would have failed and the natural recovery would have shipped the round-5 plugin), and an unbumped `PLUGIN_VERSION`
  labelling round-6 evidence as round-5 code. Verified both fixes myself.
- Kept `fused_camera.py` byte-identical: it hashes 382eee6d... in all fifteen c7/c8/c9 runs, so the three fused conditions
  provably differ only in configuration. That is why I left its stale "level" docstring alone.
- Result: c9 1/10, below c8's 2/10. Ep1 0/5 oracle 0/5; ep2 1/5 with the lowest navigation error of any head-pose condition
  (4.04 m) and below the baseline.
- The round's real finding is a limitation, not a number. Ep1 oracle by condition is 3,1,5,0,5,0 (B0,C5,C6,C7,C8,C9),
  near-unanimous within conditions and not monotone in pitch, FOV or uncovered fraction. System 2 locks a route per image
  stream; at one condition per geometry ep1 measures the lock, not the camera. This weakens C6's 5/5 as much as C9's 0/5.
- Also killed the round-5 hypothesis that uncovered pixels drive `s1_stop_mid_segment`: C9 has the most black and the
  fewest such stops.
- Manifest hygiene: the round-5b manifest's 2,892-line scope was undocumented and unreproducible (it silently excluded the
  baseline runs, other requests' runs and parts of data/). Re-verified it first (2,873/2,892 OK, all 19 failures
  round-6-owned request files, none under runs/), then stated the scope explicitly and regenerated: 3,190 lines, 0 non-OK
  both sides.
- My own watcher bug: `grep -c X || echo 0` emits two lines when there are no matches, so the first poll loop exited
  immediately and I reported the runs finished when v1 was still going. Corrected to an explicit DONE/RUNNING probe.


## Session 13: Status review and backlog evidence commit

**Date**: 2026-09-15
**Task**: Status review and backlog evidence commit
**Branch**: `main`

### Summary

Reviewed project status, then committed the Aug 18 to Sep 14 backlog: text tracked, 29,974 large files local-only with scoped ignores and per-directory SHA-256 manifests.

### Main Changes

- Status review: hot zone and journal lagged Isaac Phases B-D; everything since 3635579 was uncommitted (34,036 untracked files, 4.1 GB).
- Task 09-14-commit-backlog-evidence: Dr Sun chose text-only; classifier assigns every path to one of 10 commit groups; 15 scoped .gitignore blocks and LOCAL_ONLY_BYTES.sha256 manifests; exceptions tracked on request (3 authored episode .json.gz, 4 waypoint .npy).
- trellis-check found two classifier bugs (fresh-session rerun lost the local-only list; staged renames could drop the old path) and wrong provenance in two .gitignore comments; all fixed before staging.
- Commits 1-9 each verified against the approved list; Isaac task E.2 ticked; harness spec records the manifest convention.

### Git Commits

| Hash | Message |
|------|---------|
| `ab7c8414` | (see git log) |
| `b472a48c` | (see git log) |
| `540abf14` | (see git log) |
| `63002f85` | (see git log) |
| `0d134e49` | (see git log) |
| `0a816433` | (see git log) |
| `3cfa2189` | (see git log) |
| `7f743cfa` | (see git log) |
| `0374716f` | (see git log) |

### Testing

- [OK] 34,158-file SHA-256 snapshot: 0 unintended changes after commits; 15 manifests pass shasum -c; ignored set equals local-only set exactly.
- [OK] Probes .pdf/.png/.mp4/.zip/.step outside scoped dirs not ignored; CLAUDE.md exact; only 4 committed files over 5 MB, all .jsonl; no credential patterns in staged text.

### Status

[OK] **Completed**

### Next Steps

- Dr Sun: D.1 furnished-scene admission (scene and start budget).
- Dr Sun: playwright junk (track/ignore/delete) and the ~1 GB of Codex checkpoint refs in .git.
