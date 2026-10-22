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


## Session 14: Status review, Sep 16 decisions and Sep 15-16 evidence commit

**Date**: 2026-09-16
**Task**: Status review, Sep 16 decisions and Sep 15-16 evidence commit
**Branch**: `main`

### Summary

Reviewed project status; Dr Sun set foundation-first priorities; committed D.1b, HarnessVLN and MIP text evidence with 322 large files local-only.

### Main Changes

- Status review: corrected the reading of the SCAN defect (a terminal-acceleration replan rejection, not a collision) and of C8 (camera-ablation condition 8, the two-camera software fusion).
- Dr Sun decisions: test the SCAN fix next as a HarnessVLN child task, no 5070 Ti run before the run count is approved; Pi/Cortex waits for the navigation base; D.1b parked for discussion; MIP analyse episode 0 then 5 more episodes; older items on hold.
- Task 09-16-commit-sep15-16-evidence: classifier adapted from the Sep 15 task; 3 manifests (322 files, 937 MB); scoped .gitignore block; Dr Sun approved keeping 17 HarnessVLN text dumps over 5 MB (617 MB) local-only.
- Classifier bug caught on first run: it re-included local-only entries from already-committed manifests (4,767 false UNCLAIMED errors); fixed by subtracting each manifest's HEAD entries.

### Git Commits

| Hash | Message |
|------|---------|
| `8df243fc` | (see git log) |
| `c10f2976` | (see git log) |
| `e226be6f` | (see git log) |
| `ad9b157d` | (see git log) |

### Testing

- [OK] [OK] 39,352-file SHA-256 snapshot unchanged after the commits; the 3 manifests pass shasum -c with 0 failures; Isaac manifest only gained 37 lines.
- [OK] [OK] check-ignore: every local-only path ignored, no committed path ignored, probes outside the roots not ignored; no committed file over 5 MB; each staged list equals its approved list; CLAUDE.md exact.
- [OK] [OK] Credential scan of committed text: DEEPSEEK_API_KEY appears only as a variable name. JSON 1,346, YAML 78, Python 1,655 parse; one YAML uses DeepSeek Harness's own !!js tag (syntax valid).

### Status

[OK] **Completed**

### Next Steps

- Write the SCAN fix test child task (prd/design/implement) and bring the 5070 Ti run count to Dr Sun.
- MIP: finish the episode-0 analysis, then run 5 episodes when no Isaac test is using the 5070 Ti.
- Discuss D.1b with Dr Sun.


## Session 15: SCAN fix Isaac series, report and adoption

**Date**: 2026-09-17
**Task**: SCAN fix Isaac series, report and adoption
**Branch**: `main`

### Summary

Ran 8 Isaac cancel/resume episodes with scan_04 (7/8 pass), replayed stop poses natively, published the report; Dr Sun adopted scan_04 and opened a sim-only stance-hold task.

### Main Changes

- Isaac series on gpu5070ti: 7/8 passed the 41 checks (bound 0.529); e03 failed goal-B stillness (one 0.1595 rad/s yaw sample; V12 on zero command, no PD hold per Dr Sun).
- Native stop-pose replay: original build rejects the resume plan at 6/8 stops, fixed accepts 8/8; AC0 control reproduced.
- Report: make_report.py, make_report_page.py, RESULT.md; private page https://claude.ai/artifact/VSTvZquqTiA4iGuwWabJ6v; check pass fixed driver fail-open probe, ledger gaps and several hand-typed numbers.
- Dr Sun adopted scan_04 (PRD D14, AC7 not met as written); opened task 09-17-isaac-runner-stance-hold (Isaac runner only).

### Git Commits

| Hash | Message |
|------|---------|
| `290a0ec5` | (see git log) |
| `20f24308` | (see git log) |
| `097304f4` | (see git log) |
| `486cc80a` | (see git log) |

### Testing

- [OK] [OK] 102 scan_fix_qualification + 61 isaac_runner + 24 p2b tests pass
- [OK] [OK] 468 local-only manifest lines verified by shasum -c and all git-ignored; no staged file over 5 MB; credential grep clean

### Status

[OK] **Completed**

### Next Steps

- Stance-hold task: answer Q1-Q3 (hold pose, trigger, gains/blend source), then design.md and implement.md, then run budget.
- Pi/Cortex, D.1b and older items remain on hold; MIP halted.


## Session 16: Isaac runner stance hold: crossfade entry, two-goal 8/8, post-result AC7, default on

**Date**: 2026-09-17
**Task**: Isaac runner stance hold: crossfade entry, two-goal 8/8, post-result AC7, default on
**Branch**: `main`

### Summary

Task 09-17-isaac-runner-stance-hold closed. The xfade1s crossfade entry was selected after a survey. The two-goal series with the hold on passed 8/8 (one-sided 95% lower bound 0.688; hold-off 7/8), but the hold does not change the two-goal stop check (V12 is still settling in the review window). AC7 passes only under Dr Sun's post-result amendment D7 (window ends at a restart; as frozen, episode 6 fails at 0.174 rad/s). Launchers default to --stance-hold auto (D8). Evidence label integrated, not validated. Simulation only.

### Main Changes

- Crossfade entry xfade1s and landing grace (D6); walk entries <= 0.087 rad/s; D5 selection.
- Two-goal series 8/8 on gpu5070ti; episode 3 recovered after the local driver died (no physics re-run).
- D7 post-result AC7 amendment: thresholds 34c15fe6, amended and as-frozen verdicts side by side.
- D8: launchers default to --stance-hold auto (xfade1s); the runner default stays off; SCAN series driver and point-cloud probe pinned off.
- RESULT.md, figures, private page https://claude.ai/artifact/LbF8JD4XWmnsfgvnDbUVMM; spec section on post-result amendments and interrupted series; memory archive.

### Git Commits

| Hash | Message |
|------|---------|
| `02e4e55b` | (see git log) |
| `a826eb75` | (see git log) |
| `87f3c0d1` | (see git log) |
| `fe82a471` | (see git log) |
| `9b4bcc34` | (see git log) |

### Testing

- [OK] isaac_runner 211 tests; scan_fix_qualification 102 + 11; materializer --check clean; patched runner 0649747e unchanged; implement/check agents GO.

### Status

[OK] **Completed**

### Next Steps

- Dr Sun chooses the next foundation step. Open: the two-goal stop-dwell margin (worst 0.145 of 0.15) is set by V12 settling; no PD hold on the real robot; local clouds.jsonl copies of the stand/walk runs (~650 MB).


## Session 17: Archive sequential SCAN stair repairs at scan33 build after server shutdown

**Date**: 2026-09-26
**Task**: Archive sequential SCAN stair repairs at scan33 build after server shutdown
**Branch**: `main`

### Summary

Experiment + analysis remains in progress. scan33 native15/local+Foxy, independent review, generator parity and full build passed; install identity and real-optimizer/live tests pending. User reported server shutdown and requested archive. Local simulation capability assessed without installation or run.

### Main Changes

- Saved scan28–33 evidence boundaries, cold/hot project memory and exact resumption handoff; no staging or commit.

### Git Commits

(No commits - planning session)

### Testing

- [OK] scan33 native15 cases pass locally and in fixed Foxy; old scan32 has12 declared failures and3 positives. Full build source identity matches before and after.

### Status

[OK] **Completed**

### Next Steps

- After continuation and server power-on, capture scan33 installation identity then replay fresh/old inputs; keep MuJoCo adaptation a separate unexecuted option.


## Session 18: v6 short SCAN reference continuation

**Date**: 2026-09-27
**Task**: v6 short SCAN reference continuation
**Branch**: `main`

### Summary

Confirmed and repaired the captured 17.4 cm native continuation. Repeated native PVA/collision/negative checks and default flat replay pass. Two full Building attempts remain unsuccessful; the second reaches 90,000 physics steps, moves 0.4158 m net and does not enter final PD hold. Preserve original A4 task as in_progress.

### Main Changes

- One shared, explicitly enabled map-resolution progress predicate replaces four duplicate close-target guards; source frozen before execution.

### Git Commits

| Hash | Message |
|------|---------|
| `00be31a6` | (see git log) |

### Testing

- [OK] Native frozen-state controls and repeats pass; all declared negative cases retained; recorded-state video fully decoded and visually inspected.

### Status

[OK] **Completed**

### Next Steps

- Trace observed obstacle contributors and support/heading at the next rejected targets, then define one v7 change; audit missing backend failure terminal separately.


## Session 19: v7 minimum planned cruise 0.6 m/s

**Date**: 2026-09-27
**Task**: v7 minimum planned cruise 0.6 m/s
**Branch**: `main`

### Summary

Implemented and froze v7 minimum planned horizontal cruise 0.6 m/s with acceleration/braking/stop exceptions. Native build, 15 recorded curves, invalid-parameter checks, original short continuation, actual native retiming 0.59856 -> 0.60783 m/s and two direct 0.6 m/s walks with PD return passed. Measured steady forward mean is about 0.566 m/s, so measured minimum 0.6 is not validated. Empty full-route trial failed on initial heartbeat; original Building reached its physical bound after 0.4113 m net progress, no cruise/arrival/final PD. Retained all failures and verified v7 Building MP4. Original A4 remains open; next production repair uses v8. Scoped commit only, unrelated dirty files preserved.

### Git Commits

| Hash | Message |
|------|---------|
| `32c25642` | (see git log) |

### Status

[OK] **Completed**


## Session 20: Recover historical full Building success

**Date**: 2026-09-27
**Task**: Recover historical full Building success
**Branch**: `main`

### Summary

Dr Sun clarified the old successful video was the stair/full-floor route. Recovered machine-dog-nav native_full02: 4904 raw records, 74.062882 m XY, 98.08 s, 3.768 cm final error, stopped; original full video SHA and full decode verified. Current v7 loads the same Building/PCT assets but plans only a 46-point 5.001 m stair segment, versus the historical 631-point 73.237 m route. Isaac/native planner and Newton/reactive planner conditions differ. No runtime code or sibling repository changed. Historical sibling planner directory is untracked, so future import must use clean pinned upstream and reviewed port provenance. Same-input causal comparison remains pending; original task stays in progress.

### Git Commits

| Hash | Message |
|------|---------|
| `ce7284ed` | (see git log) |

### Status

[OK] **Completed**


## Session 21: Compare historical full Building success with Newton v7

**Date**: 2026-09-27
**Task**: Compare historical full Building success with Newton v7
**Branch**: `main`

### Summary

Read-only production audit with repeated native replays: terrain/support and retained nonterrain labels block the stair frontier; native exhaustion is not reported to the active P2B owner. Historical full route remains the control. No v8, physics run or production change.

### Git Commits

| Hash | Message |
|------|---------|
| `661b02e0` | (see git log) |

### Testing

- [OK] Original 66-scan continuation replay repeated identically; native single-label counterfactual gives occupied 1 -> 0 -> 1.
- [OK] Historical 65 manifest and 62 executed source checks; current 205 frozen source, 97 native source and 515 installed file hashes pass.

### Status

[OK] **Completed**

### Next Steps

- Repair the recorded terrain/obstacle evidence seam separately from P2B failure reporting, preserving obstacle negatives and integer versioning.


## 2026-10-02 — v57 two recordings and review delivery

Executed the two authorized90s Building recordings on idle gpu5070ti. Both pass the old corner and record46.20/46.62m with no >1s pauses, but successful local planning25.65/25.76Hz and660.975/290.149ms maxima fail30Hz/tail acceptance. All7408source/519install hashes and1590 archived members verified. Numeric analysis stays remote; compact tables support local plots. One original-state8.4MiB MP4 has full decode/frame/hash and three-preview review. Frozen v51 rendering needed exact source/reference transfer and its original font via task-local XDG font lookup; no frozen source changed. See versions/v57/RESULTS.md and provenance. Main performance objective remains open; no further physics launched and no commit made in this delivery turn.


## 2026-10-02 — v57 post-70-second diagnosis

Original two-run traces and20-state/40-search unchanged-native replay confirm a fixed-pool spatial trigger, repeated failed final-goal A* before warm initialization, and growing corridor expansion. Curve timestamp comparison establishes an inherited handover timing gap, with~1m longitudinal tracking lead and reduced30Hz controller commands. No runtime edits or new physics; verified compact audit and figure saved under audits/2026-10-02_v57_after70. Native source/install hashes unchanged; heavy replay artifacts stay on gpu5070ti.


### 2026-10-02 — v58/v59 post70 repair, physical validation waiting

Authorized by Dr Sun after the completed v57 diagnosis. v58 freezes a current necessary endpoint observation certificate; 80 paired calls retain outcomes, max goal search45.129->0.272ms. v59 freezes sampled trajectory epoch through warm/native fallback and controller receipt; 15 controller and10 epoch checks per native fixture pass, with all inherited build/safety gates. v57, v58 and v59 source/install identities preserved; no v49 budget or stop change. GPU became occupied by a separate Isaac evaluation; v58 trial01 stopped at preflight with zero physics. Dr Sun said "just wait". Next: v58 trial02 then v59 trial01 (90s each), compact analysis/plots and one review MP4. Heavy data remains remote, no commit or global-memory write. See active v59 task EXECUTION_STATE.md.


### 2026-10-03 — v58/v59 physical validation and final review delivery

Honored Dr Sun's GPU wait, then ran frozen v58 trial02 and v59 trial01 sequentially on the free host. Both 90-second requests complete, with no dropped steps. Successful planning 27.53/26.43 Hz; max solve 659.526/1236.709 ms; paths 55.19/55.04 m. Idle-host paired03 confirms final-goal-search max 44.614381 → 0.259025 ms with exact outcomes. v59 controller/native epoch tests pass; late matched handover position difference falls to at most 0.168 mm. Overall acceptance remains failed: v59 has a 1.099 s late hold while a rejected warm connector triggers repeated cold recovery and the observed old curve expires. No goal/yaw/PVA/dynamics/safety or stop-protocol relaxation, and no v49 deadlines.

Final plot uses complete pacing-window rates/latencies and includes initial navigation waiting; post-recording planner activity is excluded. Original all-log metrics remain separate. Final v61 camera is display-only, replaying exact v59 states: 2,449 frames, full decode/time-state identity and six visual samples verified. One 10,488,224-byte MP4 returned, SHA03ade05cdc1f51e9c75650cb686f85dcfed6d53e8271ab3a9e6832814f8acc1a; failed camera renders and all heavy logs/state/builds remain remote. See versions/v59/REPAIR_REPORT.md and versions/v61/REVIEW_VIDEO.json. GPU-wait heartbeat paused. Native versions remain frozen; no commit or broad staging. Main performance/continuity task remains open for review of the remaining cold-recovery chain.


### 2026-10-03 — v59 cold-recovery root-cause audit

Dr Sun requested diagnosis only. Native recorded-input replay confirms the remaining curve is clear, but the proposed connector reorients its front footprint into an intentional drop exclusion at sample0. The first shorter target has a clear fitted initializer; optimization moves it into collision, and failed constraint generation is repeated three times per ordinary/fixed-height attempt because its failure status is not propagated. Live trace has six such failures in an eight-attempt,1236.709ms round. A separate v59 defect retains the81.027099609s sampled PVA across retries but assigns82.286407471s after the old curve expires; prior "fresh restart" interpretation corrected. Two37.6s CPU native probes plus5.1s static guard witness, frozen sources unchanged; one-ULP preparation failure preserved. No physics/new version/production repair. Compact audit and corrected acceptance/report links saved; heavy data remote. Main task remains open.


## Session 22: Mac planner repair: retry epoch and failed optimizer search

**Date**: 2026-10-04
**Task**: Mac planner repair: retry epoch and failed optimizer search
**Branch**: `main`

### Summary

Continued authorized main task locally while gpu5070ti was busy. Frozen v62 (native parent v59) keeps original sample epoch through eight actual retry calls: rebasing1.259307862s->0,34 checks. Frozen v63 (parent v62) explicitly propagates optimizer repair failure: actual optimizer/LBFGS fixture searches3->1 in both height modes,40 checks. Both native eight-package builds and all available Mac/recorded component suites pass; failed fixtures/build attempts are preserved. Full original corner/physics/max-latency/30Hz qualification remains pending, protected-heading connector unresolved, v48 reference retained. No GPU access, heavy downloads, commit or broad staging. Owned temporary Docker builds removed; source/snapshot identities verified. v63 active task remains in progress.

### Git Commits

(No commits - planning session)

### Status

[OK] **Completed**


## Session 23: Actual Newton Mac validation and heartbeat failures

**Date**: 2026-10-04
**Task**: Actual Newton Mac validation and heartbeat failures
**Branch**: `main`

### Summary

Dr Sun authorized Newton on Mac. Exact nativev63 with original v59 physics/backend ran in frozen hostv67/v68. Actual routes end31.614/46.506s via original heartbeat_stale, successful16.815/18.606wallHz, max494.716/836.683ms, path13.197/22.742m. Controller remains near30Hz; matching backend receipt needs trace. Earlier host-entry and cold-scan failures preserved. Clock-domain-aware plots/report/provenance delivered; full90s/post70s/30Hz validation remains pending. No native/goal/stop/safety changes, GPU use, broad staging or commit. Raw archives outside repo; all owned containers and63MB temporary build removed. v48 reference and main task in_progress retained.

### Git Commits

(No commits - planning session)

### Status

[OK] **Completed**


## Session 24: Mac heartbeat and planner bottleneck diagnosis

**Date**: 2026-10-04
**Task**: Mac heartbeat and planner bottleneck diagnosis
**Branch**: `main`

### Summary

Verified original active identities during stale-heartbeat gaps; replayed original gate dispatch/latch mechanism. Frozen observation-only v70 reaches 90,000 integrations without heartbeat fault, but23.423Hz/max1316.856ms still fail main performance acceptance. Measured cold recovery/cloud work and repeated PCT-history JSON overhead; exact old DDS/OS/GIL delay remains unproven.

### Main Changes

- Added verified capture/serializer/gate-order/trace analysis and detailed report; preserved frozen v68/v70 and failed pre-physics launches.

### Git Commits

(No commits - planning session)

### Testing

- [OK] Original gate replay10 assertions; actual original callback/JSON/error seam;4 entry tests; manager chain;8-package exact-native build and source/install gate; complete diagnostic trace0 drops.

### Status

[OK] **Completed**

### Next Steps

- Compact frequent state responses and preserve full route history once; protect heartbeat reception under diagnostics; reduce cold recovery/input work without v49 timeouts or safety relaxation.


## Session 25: Upstream SCAN Mac test and actual failure video

**Date**: 2026-10-04
**Task**: Upstream SCAN Mac test and actual failure video
**Branch**: `main`

### Summary

Pinned upstream ROS2 core tested in Mac Newton; early native planning failure recorded and video delivered, with verified remote raw storage.

### Main Changes

- Frozen v71 upstream core/transport; v72 floor publisher host key only; v73 display-only replay. Production v48 reference preserved.

### Git Commits

(No commits - planning session)

### Testing

- [OK] Six-package native build, six actual transport/cancel checks, four entry/storage tests, actual manager retention, two parser tests, actual Newton trial, source/install hash gates and 135-frame full decode/causal/visual verification.

### Status

[OK] **Completed**

### Next Steps

- Diagnose original upstream startup rejection and design a matched later-corner comparison; preserve current safety contracts and avoid v49 timeouts. Main30Hz repair remains open.


## Session 26: Corner-start current and upstream tests with verified videos

**Date**: 2026-10-05
**Task**: Corner-start current and upstream tests with verified videos
**Branch**: `main`

### Summary

Started both arms beside the recorded late corner; current planner crosses it but misses 30 Hz, upstream moves briefly then stalls with an incomplete ACK/copyback failure. Both actual review videos and durable raw evidence are delivered; the main planner repair remains in progress.

### Main Changes

- Frozen v74/v75 corner attempts preserve unavailable raw and failure boundaries; v76/v77 archive physical evidence before rendering and preserve original goal/yaw/PVA/safety/stop behavior.
- Returned compact report, current time-series plot, source and video checks, updated task/spec/index, exact MP4 ignores and remote regeneration provenance. v48 stays the reference; no GPU job or commit.

### Git Commits

(No commits - planning session)

### Testing

- [OK] Current eight-package and upstream six-package builds, actual source/install gates, available Mac component subset, six upstream transport/cancel checks and frozen source/snapshot identity verification pass; original incomplete physical failure remains failed.
- [OK] Actual v76: 20.035 m, 14.700 successful wall Hz, corner max397.826 ms, later max1307.535 ms; v77: 1.130 m, 10/1226 successful chains, max311.138 ms, original receive/ACK and copyback fail.
- [OK] Both MP4s pass full decode, causal frame/time/state checks and visual review; all288 raw/render files225114094bytes remote SHA-verified. Current local/install identities pass before383897473 temporary bytes are removed; compact failures retained.

### Status

[OK] **Completed**

### Next Steps

- Profile repeated input/cloud/map processing across cold recovery while preserving newest occupancy/support validation, trajectory continuity and every final safety gate; main30Hz and full-route acceptance remain open.


## Session 27: Map-processing spike diagnosis and native replay v78

**Date**: 2026-10-05
**Task**: Map-processing spike diagnosis and native replay v78
**Branch**: `main`

### Summary

Verified the original977ms scope is twelve synchronous refreshes containing seven new scans. Native replay identifies voxel fusion/inflation and sliding-cell clearing as intrinsic hot paths; the full original live multiplier remains unresolved and no production optimization is claimed.

### Main Changes

- Frozen observation-onlyv78, parentv76/nativev63, with exact source reconstruction and map state parity. Kept v48 reference and all goal/yaw/PVA/safety/stop rules.
- Recorded original input flow, exact wire/config comparison, per-stage timings and operation counts, report and task/spec/version state. Original heavy data and full profiling/runtime remain remotely retained.

### Git Commits

(No commits - planning session)

### Testing

- [OK] Two map dependency packages and both probe builds pass; three runs per arm replay188scans. All six final buffer/history digests match and all116source/snapshot identities verify.
- [OK] Seven scans:926950fusedvoxels,905074occupancycalls,25175190inflationneighborvisits,3actualshifts/21checks clearing474416cells. Unmodified idle batch266.600–312.992ms does not fully reproduce live976.721ms.
- [OK] Original wire poses/cloud widths/config and three support payload hashes verify. All21retained result/runtime files3436644bytes remotelySHAverified;120935798temporaryMacbytes removed after current source/input/install/result identities and container closure pass.

### Status

[OK] **Completed**

### Next Steps

- Measure per-refresh/per-cloud live timing, actual shifts and cache sizes/clear cost to separate the remaining live multiplier; then optimize proven operations with decision-boundary state and safety equivalence. Main30Hz/continuity repair remains open.


## Session 28: Compact polling and asynchronous mapping repair, failed continuity

**Date**: 2026-10-05
**Task**: Compact polling and asynchronous mapping repair
**Branch**: `main`
**Stage**: experiment + analysis

### Summary

Implemented the four authorized changes as frozen v79–v82; builds and component
safety/equality checks pass. Two actual 90-second Mac corner runs preserve
heartbeat but fail trajectory continuity and 30 Hz. v82 is a failed candidate;
v48 remains the reference and the main task stays in progress.

### Main Changes

- v79 compact polling and once-per-plan full evidence; v80 equivalent voxel,
  inflation and sliding arithmetic; v81 immutable map snapshots and newest-map
  publication validation; v82 fixed-point duplicate reduction only with backlog.
- Display-only v83 renders the actual failed trial01 as a verified MP4. Returned
  report, plots, specification and exact remote storage/cleanup receipts.
- No v49 deadline, stop-protocol change, safety age relaxation, GPU compute or
  real-robot actuation. Goal/yaw/PVA/dynamic/support rules are preserved.

### Git Commits

No commit: a pre-existing Git index lock and other Git activity were observed.
The lock and unrelated work remain untouched; no automatic session commit.

### Testing

- [OK] Eight native packages; 23 Python/HTTP/backend checks; actual 360 polls at
  30 Hz keep callbacks healthy. The original 200 ms heartbeat fault still latches
  when input stops.
- [OK] Three 188-scan paired runs and 14 sliding phases preserve every map/history
  state. Original native/cache/endpoint/controller/recorded suites, 26 snapshot
  checks and 20 backlog checks pass; all 188 moving observations are retained.
- [FAILED acceptance] Two 89.962 s Mac runs: 11.114/10.959 useful Hz,
  491.143/312.939 ms maximum solves, 23.787/31.283 s longest pauses and 850
  emergency transitions each. No heartbeat_stale. Mapping breaches the unchanged
  250 ms scan validity interval and causes holds; neither run records arrival.
- [OK] Review MP4: 2,707 causal frames, 90.233 s, full decode and visual QA.
  All 343 files / 590,903,005 bytes remotely SHA-verified; 1,028,377,799 owned
  temporary bytes removed after identity/process checks. All 41,402 source and
  snapshot pairs pass after cleanup (82,804 individual hashes).

### Status

Review handoff delivered; main continuity/30 Hz repair remains **in progress**.
No navigation acceptance promotion.

### Next Steps

Review async mapping throughput and handover before adoption. Keep v48 runnable
and v82 failed evidence; do not broaden frame loss or relax freshness to mask
the regression.

## Session 29: Mapping admission comparison and separated-lane prototype

**Date**: 2026-10-08
**Task**: 10-04-newton-v64-mac-physics
**Stage**: experiment + analysis

Dr Sun approved the two upstream-backed investigations. v84 runs the same 188
recorded scans through exact native mapping with FIFO, timer/latest and latest
admission. Plain latest-only loses obstacle evidence and is rejected; a native
transient-only fixture demonstrates the missed obstacle. Completion-time source
age and held-map age are separately recorded; stale exposure remains.

v85 implements a separate three-thread component prototype. Its 26 checks and
actual recorded replay pass: all frames retained, original map hash recovered,
sensor and execution decisions continue during mapper stalls, and stale maps
never receive an allowance in the checked windows. No actual command publisher,
full moving-trajectory/braking integration, physics, training or robot action.

The first temporary environment disappeared after an interrupted turn; cause is
unknown and missing raw evidence is disclosed. Recreated attempt02 uses the
original verified archive and returns compact results after every arm. Original
v82 source/install identity is checked; heavy evidence/runtime is archived to
gpu5070ti storage with per-member hashes. See the 2026-10-08 mapping-admission
report and storage receipt. v48 remains the reference, v82 remains failed, and
the main continuity/30 Hz task stays in progress. No automatic commit or staging
of the large pre-existing dirty worktree.

### Planning continuation: fixed Foxy deployment design

Dr Sun selected the existing Jetson with Ubuntu 20.04 and ROS 2 Foxy. The
reviewable design and Chinese overview are in
`.pipeline/design/2026-10-08_nav2_foxy/`. Eleven Nav2 0.4.7 fixed-commit files,
the root package tree, official Foxy release/platform records and current local
P2B contracts were inspected; source hashes are retained. Official BT task
orchestration is the first increment, while PCT/SCAN and the sole command/stop
path remain authoritative. Cancellation requires controller hold and measured
stillness before new ownership. Mapping throughput and full motion remain open.

This continuation is planning only: no executable import/build, runtime version,
Nav2 integration, robot action, training, staging or commit. Existing task stays
in progress; the next implementation gate is target inventory plus a Foxy mock
adapter build. See `NAV2_FOXY_DESIGN_20261008.md` in the active task.

## Session 30: Foxy SCAN plugins and Nav2 observation scheduling

**Date**: 2026-10-08
**Task**: 10-04-newton-v64-mac-physics
**Stage**: implementation + component analysis

Dr Sun requested actual pluginization and Nav2-style mapping backlog handling.
v86 exports Foxy controller/goal plugins, owns the native SCAN planning executor,
and preserves tagged output and physical-stop authority through a narrowly
pinned ControllerServer adaptation. v87 adds temporal observation buffering and
periodic native 3D map updates. Original frozen versions remain unchanged.

ARM64/Foxy builds, 18 GoogleTest cases including 300-sample tracking parity,
actual server protocol/launch checks, 37 actual ObservationBuffer checks, native
safety emission and six transient cases have direct evidence. The server protocol
uses synthetic planner/TF/stop proof. Two three-arm 188-scan native replays retain
FIFO parity; the selected 0.5s window loses 2 scans and 23 occupied cells, and
map-age intervals still exceed the unchanged 250ms gate. This is not a complete
navigation repair or a Jetson/robot result. Current remains v48; main task stays
in progress. Source/compact reports are local; bulk evidence is archived with
hash receipts under the 2026-10-08 Nav2 Foxy plugin audit. Existing index.lock and
the two pre-existing staged files are preserved; no commit or broad staging.


## Session 31: Full Nav2 Foxy integration and failed original physics

**Date**: 2026-10-08
**Task**: 10-04-newton-v64-mac-physics
**Stage**: implementation + experiment analysis

Dr Sun approved full Nav2 integration on the existing Ubuntu 20.04/Foxy Jetson.
Access is unavailable today and will be supplied later. v88-v99 preserve all
frozen parents and add the actual PCT GlobalPlanner, SCAN controller, native-map
TerrainLayer, BT binding/measured-stop recovery, public mission gateway and
legacy HTTP adapter. PCT runs natively on ARM64/Python 3.8. Native scan replay,
stock Nav2 control and full mission protocol checks remain separately labelled.
Normal 188-scan FIFO and 20 Hz window replays retain the exact final map and
about 100 ms max sampled age; injected stalls remain stale and fail closed.

The portable source export builds 14 packages from scratch and passes 25 GTest
cases (28 colcon entries including wrappers). Its fresh install repeats native
PCT goal/cancel/input checks, with explicitly synthetic SCAN curves/map/safety.
Real-plugin failing regressions reproduce and repair missing repeated cancel
ack before a first spline and identical timestamps falsely classified as future.
Future/stale negatives retain the original thresholds. Newton sensor precompile
preserves ray outputs, physical state and sequence/time without publishing probes.

The original Newton scene is connected but NOT accepted: v95-v98 have no walking
commands. v98 no longer shows timestamp-rounding faults; native startup/trajectory
safety rejects remain, followed by an applied-state transport timeout. Its final
Linux state differs from the last acknowledged bytes, so copyback fails. Both
copies and all failures are retained. No complete route, steady 30 Hz, Jetson
receive-only or robot motion claim. See the full Nav2 audit report and STORAGE.json.
Current v48 and the main in-progress task remain. The pre-existing index lock,
staged v34/v35 records and unrelated dirty work remain untouched; no commit.

Retention closeout: archive425237207bytes /20689members remotely SHA-verified;
local members reverified and1536405652temporary/archivebytes removed. Owned
container/image removed, baseFoxy retained. See STORAGE.json/RESTORE.md; no exact
Docker image export claim. Source/code and compact evidence remain local.


## Session 32: Nav2 original Newton arrival with two protected retries

**Date**: 2026-10-08
**Task**: 10-04-newton-v64-mac-physics
**Stage**: experiment + analysis

Dr Sun rejected component-only delivery and required the original simulation to
work. Continued inline with no subagents. Frozen v100-v114 preserve the original
scene, robot policy, inputs and safety limits. Diagnosed real clock/body ordering,
replan safety state, output-ticket races, Foxy executor shutdown and applied audit
I/O. Recorded-map CPU profiling led to equivalent inflation optimization with268
per-frame and14 sliding-boundary hash matches. Independent native collision
validation in the Nav2 controller removes its dependence on the planner safety
timer's scheduling; each command retains owner/trajectory/map/body timing checks.

v114 actual original-scene run travels26.551m, reaches goal and completes measured
stop. XY error0.128538m, Z error0.013565m; no fall; applied copyback passes. Two
protected stop/retries remain (future controller-body input and254.86ms map age).
Six affected packages rebuilt over verified14-package Foxy/ARM64 underlay;
34colcon entries/31GTest cases and actual native map/proof regressions pass.
v115 review MP4 is54.833s/1645frames, actual wall1:1 state replay, no interpolation
or new physics; full decode and visual inspection pass, final arrived visible.

Main30Hz/continuity/repeatability acceptance remains open; referencev48. Jetson
access remains unavailable per user; no robot motion or GPU jobs. Current exact
runtime and all failed recordings are retained; bulk archive status in the audit
STORAGE.json. Existing index.lock, staged v34/v35 and unrelated work are preserved.
No commit or broad staging. See audits/2026-10-08_nav2_sim_repair/REPORT.md.

Retention verified: archive1099739984bytes, all30605members and manifest checked
on gpu5070ti; storage only. Local runtime/raw roots retained for continuation.
Docker execution image remains local and is explicitly excluded from the archive.


## Session 33: Visible native local curves and offline timing HTML

**Date**: 2026-10-09
**Task**: 10-04-newton-v64-mac-physics
**Stage**: experiment + analysis

Dr Sun requested local planning curves in the video and an HTML latency plot.
v114's prior successful run had no final Bspline records: the recorder used the
old unnamespaced topic. v116 fixes recording only and preserves exact v114 native
source/install/config/policy. Actual DDS regression confirms old0/new3 exact curves.
Attempt01 records774 curves then fails transport/copyback. Attempt02 completes
recording with904 splines (895 normal,9 emergency holds) and900 timed rounds,
but navigation fails after three protected stop/retries. Do not mix it with the
previous v114 success. Both raw attempts (540members,260174054bytes) are remotely
SHA-verified on gpu5070ti, storage only.

v117–v119 establish causal controller-admitted curve display and complete-round
Matplotlib timing HTML. Visual QA exposed curve/global-route overlap and later
start-camera occlusion. Final v120 uses thick cyan markers at unchanged sample
coordinates and the original close camera; start/stair/final visibility and full
MP4 decoding pass. Video53.366667s/1601frames;903 frames show a local curve.
v121 final HTML embeds this video and all900 timing points, preserves gaps/spikes,
offers log/linear view, hover, CSV and causal seeking. Median1.580ms, P95 4.081ms,
max138.782ms; six over33.333ms and five failed computations. Four selector tests,
900 actual seek cases, unchanged source/frame hashes and final browser checks pass.
Browser confirms curve409/latest1.20ms at15s with no console error. Offline HTML
and separate MP4 are under output/2026-10-09_nav2_local_planning/delivered/.

No planner/safety change, new navigation acceptance, Jetson validation, actuation,
GPU job, subagent or commit. v48 remains reference and the main task in_progress.
Existing index.lock and unrelated staged/dirty paths preserved. See the local
curve timing audit REPORT.md and STORAGE.json. Local preview uses loopback8848;
the delivered HTML is self-contained and does not depend on that server.


## Session 34: Adopt v232/v233 and close PCT SCAN milestone
<!-- trellis-session: v=2 fp=df92bb2deafbf8ae -->

**Date**: 2026-10-17
**Task**: Adopt v232/v233 and close PCT SCAN milestone
**Branch**: `main`

### Summary

Dr Sun adopted the single original-route v232/v233 baseline; archived the traversability parent and two children; refreshed hot/cold memory with the full support, scoring, GPMP, feedback and exception-repair chain. v219/v220 retained; sustained30Hz, repeatability and physical feedback benefit remain unvalidated.

### Main Changes

- Commit physical results/videos and coherent README/current.json selection as c7294f8f.
- Archive three completed scoped tasks with acceptance map, version/commit provenance and remaining gates.
- Preserve previous hot-zone bytes, add four cold records and four reversible aging summaries; update reusable workflow/spec contracts.

### Git Commits

| Hash | Message |
|------|---------|
| `c7294f8f` | docs(nav): adopt v232-v233 single-route physical baseline |
| `ff4cb515` | fix(nav): contain native exceptions and close failed missions |
| `e9f8bec0` | feat(nav): retain mission-scoped local blockage feedback |
| `420a0ff9` | fix(nav): align GPMP height with native support layers |

### Testing

- [OK] 73 delivery file hashes and both frozen source manifests pass; no compiler caches.
- [OK] All three archived task context validators pass; hot-zone capacity and parent/child/source links checked.

### Status

[OK] **Completed**

### Next Steps

- No new experiment started. Select a separate future scope for sustained frequency, repeated control or physical feedback exercise.


## Session 35: gpu40901 v234 offline migration and v235 physical failure evidence
<!-- trellis-session: v=2 fp=ccdfce8eb5a682a2 -->

**Date**: 2026-10-17
**Task**: gpu40901 v234 offline migration and v235 physical failure evidence
**Branch**: `main`

### Summary

Offline migration passed. Exactly one v235 physics attempt failed at captured-scanner deadline; final saved state12.802s before goal dispatch. Verified partial and comparison videos returned; no baseline adoption or automatic rerun.

### Main Changes

- Prepared frozen v235 host entry using v234 rebuilt v232 runtime; preserved RL/endpoints/0.35m guards.

### Git Commits

| Hash | Message |
|------|---------|
| `114ce97f` | feat(sim): migrate v232 runtime to gpu40901 with verified offline gates |
| `2156007d` | test(sim): record gpu40901 v235 scanner-deadline failure and comparison videos |

### Testing

- [OK] Actual12s graph/profile preflight passed; source manifests and54 returned payload hashes exact; causal video/full decode/visual checks passed. Physical route gate failed,45-55s stairs and terminal PD untested.

### Status

[OK] **Completed**

### Next Steps

- Keep migration task open; diagnose scanner timing under own2-CPU binding before separately authorizing any new physical trial.


## Session 36: v236 LiDAR deadline repair and failed single-route writer-backlog trial
<!-- trellis-session: v=2 fp=aa28be1bd1a5d712 -->

**Date**: 2026-10-17
**Task**: v236 LiDAR deadline repair and failed single-route writer-backlog trial
**Branch**: `main`

### Summary

Reproduced native-clock early rejection and hot two-core contention; repaired absolute100ms LiDAR scheduling and verified own4-CPU wrapper. One physical attempt completes245 scans with no deadline failure, then fails at35.592s on the original evidence-writer queue bound. Four-way comparison returned and verified; v232/v233 baseline retained.

### Main Changes

- Preserve original RL/endpoints/.35m guards/.1s capture; change only own scheduling and recorder deadline boundary.
- Correct partial audit reporting to read the original FAILED finish_request; retain first-pass reports and all raw capture files.

### Git Commits

| Hash | Message |
|------|---------|
| `bcc43b6a` | fix(sim): preserve absolute LiDAR deadline and isolate gpu40901 CPU scheduling |
| `40e1cecd` | test(sim): record v236 writer-backlog failure and four-way physical comparison |

### Testing

- [OK] Seven regressions;550 zero-physics original-ray/catch-up cases; ray bytes and1000-frame policy golden; actual source/install/profile/12s graph preflight pass.
- [OK] 245 actual scans, max46.719ms; physical route fails35.592s, stairs/arrival/PD untested.61 returned payload hashes/sizes, MP4 full decode and visual samples pass.

### Status

Scanner repair and evidence delivery completed. **Physical route failed; migration task remains in_progress.**

### Next Steps

- Diagnose shared critical-state/bulk-evidence writer queue without relaxing256 bound; offline verification before another separately authorized physical trial. Task stays in_progress.


## Session 37: Return to gpu5070ti and validate one v237 original route
<!-- trellis-session: v=2 fp=2988cc8a904e18c4 -->

**Date**: 2026-10-17
**Task**: Return to gpu5070ti and validate one v237 original route
**Branch**: `main`

### Summary

At user direction, return from shared40901 to the original5070Ti environment. v237 combines original v232 native/v233 host binding with the v236 scanner deadline repair. One continuous original route passes FINISHED at124.223358s, final PD4.377594s; all1132 LiDAR jobs meet100ms. Same-host three-way videos and77 declared payloads verified locally.

### Main Changes

- Freeze eight current/source snapshot files and parent diff; verify original317-source/607-installed identities, unchanged RL/endpoints/.35m guards/.1s captures.
- Preserve first display-layout rejection; adapt only version-relative manifest resolution and retain every current/snapshot hash check. No second physics run or shared job mutation.

### Git Commits

| Hash | Message |
|------|---------|
| `6a9e531c` | feat(sim): bind the scanner-repaired original route back to gpu5070ti |
| `10fe2631` | test(sim): record v237 original-host route pass and same-host comparison videos |

### Testing

- [OK] Seven regressions,250 zero-step ray/catch-up cases, policy golden and actual12s graph/profile pass. Original route/terminal gate passes; XY0.118992m;45–55s296/296 rounds, zero measured pauses>=1s; minimum extra edge margin0.128963m.
- [OK] 3720 actual video frames,3728 comparison frames,301 stair frames; full decode, causal/source/quality cross-hashes,77 payload hashes/sizes and direct visual checks pass. Sustained30Hz/full qualification remain false.

### Status

[OK] **Completed**

### Next Steps

- Human review of v237 candidate; default future execution to gpu5070ti. Preserve v232/v233 accepted selection and unresolved40901 backlog evidence. Migration task remains review, not archived as a40901 physical pass.


## Session 38: v240 terminal continuity and one v241 full physical route pass
<!-- trellis-session: v=2 fp=4c977577cde2cb8c -->

**Date**: 2026-10-18
**Task**: v240 terminal continuity and one v241 full physical route pass
**Branch**: `main`

### Summary

Committed v238 attribution, retained rejected v239, froze v240 input-delivery repair. One authorized gpu5070ti v241 original-route run passed at121.424896s with4.357605s measured PD, zero approach emergency/>=0.5s pauses and zero stair pauses. Stair minimum extra margin0.129810m versus v237 capped0.15m;95% at cap. Four source-verified videos returned. RL/endpoints/.35m/.1s/v237 scanner unchanged; no retry, baseline promotion or sustained30Hz claim. Unrelated dirty harness files and v221 preserved.

### Git Commits

| Hash | Message |
|------|---------|
| `b709a7d6` | fix(nav): preserve forward reference progress and audit terminal pauses in v238 |
| `e5f640ba` | fix(nav): deliver queued inputs on stable search snapshots in v240 |
| `80d4f74a` | feat(sim): bind frozen v240 to one original-host physical trial in v241 |
| `fe04bd31` | test(sim): validate v240 approach continuity on one full physical route |

### Status

[OK] **Completed**


## Session 39: Preserve v242-v290 locally and close delivered research tasks
<!-- trellis-session: v=2 fp=e57fc3e5e6571f86 -->

**Date**: 2026-10-22
**Task**: Preserve v242-v290 locally and close delivered research tasks
**Branch**: `local/research-unpublished`

### Summary

Committed versioned source and compact evidence locally; retained all original payloads with hashes. Archived eight delivered tasks with failed acceptance, kept v290 in review, refreshed hot-zone state and preserved its prior snapshot. No GitHub push, new experiments or baseline change.

### Main Changes

- Source/evidence commit contains 49 version directories and 18 audit directories, with media/full logs/sample data retained in place.
- Preserve failed outcomes separately from administrative task completion; accepted baseline remains v232/v233.

### Git Commits

| Hash | Message |
|------|---------|
| `77d4ca08e` | chore(research): preserve v242-v290 sources and compact evidence locally |

### Testing

- [OK] Verified 42 frozen manifests and 2494 declared source entries; local payload retention is checked by the committed read-only verifier.

### Status

[OK] **Completed**

### Next Steps

- Review v290 unified terminal centering/braking and scanner deadlines; no new physical run is authorized by housekeeping.


## Session 40: v291 terminal control and pre-PD settling qualified offline
<!-- trellis-session: v=2 fp=f340685cbe08c624 -->

**Date**: 2026-10-22
**Task**: v291 terminal control and pre-PD settling qualified offline
**Branch**: `local/research-unpublished`

### Summary

Unified terminal command ownership and added loaded-leg zero-command assistance. Native 14-package suite, 29 Python tests, D07/CD12 recorded replays and strict53 passed: 49/50 legal, 3/3 illegal, 1.421 s median, independent geometry passed. HTML is 4/12 complete. Zero new physics; next select held-out routes and fix paired physical configuration. Local research hold retained.

### Git Commits

| Hash | Message |
|------|---------|
| `8ed419314` | feat(research): unify v291 terminal control and qualify settling offline |

### Testing

- [OK] Native components + Python29 + recorded D07/CD12 + strict53 passed; no physics

### Status

[OK] **Completed**

### Next Steps

- Select four unseen routes and freeze physical configuration before 24 paired runs.
