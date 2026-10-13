# Experiment Records

> ⚠ [未门控] Codex CLI 0.153.3 在当前沙箱初始化 app-server 时返回 Operation not permitted，未产生独立核查结论。主会话已核对摘要、实测字段、视频 SHA 和未实施方案边界；reviewed: false 保留。

- [`2026-10-01_newton_nav2_timing_archive.md`](2026-10-01_newton_nav2_timing_archive.md)
  — v36-v46 Nav2 timing/CPU-graph/cache integration and actual-wall video.
  v40 CPU graph exactly matches 200 original closed-loop rows; CUDA v38 fails
  its fixed-target joint gate and is not adopted. Native v44 recorded replays
  pass safety/geometry checks at 11.8/12.8 ms, but complete physical v45 runs
  at local 16.86 Hz, raw controller 29.96 Hz, global PCT 1.00 Hz and RTF 0.9400,
  ending `global_refresh_failed:pct_no_route`. v46 delivers an ordinary
  57-second wall-timeline video; display 30 FPS/1:1 playback proves neither
  local 30 Hz nor simulation 1:1. No Building arrival; v3 remains accepted.
  Optimization proposals are archived, not implemented; v47 absent.

- [`2026-09-26_newton_stair_reproduction/versions/v32/`](2026-09-26_newton_stair_reproduction/versions/v32/RESULTS.md)
  — 2026-09-29 v32 (Dr Sun: fix the clock fault). The [wall-clock chain diagnosis](2026-09-26_newton_stair_reproduction/audits/2026-09-29_wall_clock_chain/RESULT.md)
  split the `odom_stale` gaps into two mechanisms:
  - **A:** full cyclic garbage collections in the Mac worker that hold the GIL for 99–176 ms.
  - **B:** CPU-starvation slowdowns under host load, plus poses superseded after publishing.

  v32 collects and then freezes the worker's heap before the loop and every simulated second. Only
  `scripts/newton_episode.py` changes, with three insertions. It passed a byte-exact check, an AST scope check,
  a three-schedule replay and five independent review rounds.
  - **Instrumented run (L1):** inconclusive by its exposure rule (2,818 of 7,100 steps). It had no automatic
    full collection, no process-wide hold and no collection over 16.4 ms. It ended on `odom_stale` after the
    bridge held a pose for 254.5 ms in a 288.5 ms publish callback while the host was starved.
  - **Trial (L2):** failed. It climbed both flights, then stood at the upper corridor entry from 39.3 s. Every
    curve from there was rejected at v30's wrong-height navigation cell (47, 41). After 286 s of physics it
    ended on `odom_stale`: a 320 ms worker-side stall during a burst of another session's `git diff` runs in
    `machine-dog`.
  - **Status:** mechanism A is gone where measured and B remains. v3 remains accepted.
- [`2026-09-26_newton_stair_reproduction/versions/v31/`](2026-09-26_newton_stair_reproduction/versions/v31/RESULTS.md)
  — 2026-09-28/29 v31 (Dr Sun's option 1 after the stop diagnosis, with the narrower means he kept after the
  first independent review): SCAN takes the pending pose and scan messages at safe points on its
  single-threaded executor and applies them in stamp order through the unchanged callbacks; the FSM refreshes
  its own odometry at its timers. The first candidate (scan63) failed its review and is kept in `attempt01/`;
  the second (scan64) is byte-exact. The red/green contract (mid-call and split-batch cases included) passes
  after one recorded analyzer correction; saved states and the full native regression give v30's outputs; a
  round-2 independent review passes. The live run climbs both stair flights with none of the stale-input
  stops v30 had there (8 conflict stops in the same 29.9 s) and ends on `odom_stale` (a 0.288 s wall pause
  after three clock-observation reconnects) before the upper landing, 7.12 m short. No arrival; v3 remains
  accepted. The corridor, where most v30 stops were, was not reached.
- [`2026-09-26_newton_stair_reproduction/versions/v30/`](2026-09-26_newton_stair_reproduction/versions/v30/RESULTS.md)
  — 2026-09-28 v30 (Dr Sun's option 1 after the landing-stall diagnosis): in SCAN's step score, a present
  neighbour without the walkway level is a possible drop only if the pinned surface evidence also lacks a
  surface near that level. The red/green support contract (17 cases, a node real-drop negative, a mutation
  check), the frozen landing and onset states, the saved start states, the full native regression and a
  third-round independent review pass. The live historical run crosses the upper landing (frontier 15.64 s,
  was 8.645 s) over a 13.44 m path. It then stops 4.15 m short in the upper corridor on invalid-curve holds
  and fails `odom_stale` at 69.35 s. No arrival; v3 remains accepted. On this map v30 leaves no Unknown
  support, so the trial cannot test drops. The [stop diagnosis](2026-09-26_newton_stair_reproduction/audits/2026-09-28_v30_stop_classes/RESULT.md)
  replays four frozen stops. With fresh inputs the curve's current point was clear at all four. The stops
  and holds most likely come from SCAN's input-age gates (pose > 0.1 s, processed scan > 0.25 s; the scan
  age at the stops is inferred) while planning blocks its single-threaded executor. 109 of 112 reproduced
  collision rejections hit one navigation-ground cell recorded at the landing height.

- [`2026-09-26_newton_stair_reproduction/versions/v29/`](2026-09-26_newton_stair_reproduction/versions/v29/RESULTS.md)
  — 2026-09-28 v29 (Dr Sun's choice): the known-footprint waiver is tested at the queried point, up to the
  Mid-360 origin (+0.10854 m, pinned URDF). Red/green waiver contract, all 7 saved walking-start states,
  the full native regression and an independent re-review pass. The live historical run leaves the start,
  climbs 1.31 m of stairs over a 9.77 m path, then fails `native_replan_exhausted` at 88.3 s on the upper
  landing. No arrival; v3 remains accepted. The [landing-stall diagnosis](2026-09-26_newton_stair_reproduction/audits/2026-09-28_v29_landing_stall/RESULT.md)
  replays the frozen states. The PCT route runs on the walkway's outer ring of cells, which SCAN's step score
  marks Unknown support (neighbouring cells carry only other floors). A probe-only relabel of those layers
  lets the continuation move. The v30 scope is Dr Sun's choice.

- [`2026-09-26_newton_stair_reproduction/versions/v28/`](2026-09-26_newton_stair_reproduction/versions/v28/RESULTS.md)
  — 2026-09-28 v28: the saved-input replay isolates v27's crash (seed 269, `back()` on an empty
  rebound-constraint list) and restores scan_27's lost guard. Red/green goes 10/13 -> 13/13;
  96 seed replays and the full native regression pass, with an independent review. The live
  historical run has no native crash but fails `odom_stale` at 15.56 s after a 0.344 s
  control stall. The planner still thrashes at the start; no route progress. v3 remains accepted.

- [`20260928_newton_v8_v27_archive.md`](20260928_newton_v8_v27_archive.md)
  — v24 short stair arrival without final PD; v26 automatic-layer loader repaired;
  v27 native seed regressions pass but full-route physics segfaults near13.24s.
  Execution archived/stopped; v28 not created. [未门控] Inline main-session archive.

- [`2026-09-26_newton_stair_reproduction/`](2026-09-26_newton_stair_reproduction/README.md)
  — Local Newton continuation with the original Building, sensor rig and official
  animated human. Unchanged SCAN33 builds in cached Humble and produces one
  moving curve on each original recorded-input condition; native PCT executes.
  Original-scene stance and upstream-backed geometric sensor controls pass.
  MAVROS-derived clock mapping and original-schema ZeroMQ state transfer now
  connect the actual local loop. `stair_native_walk_v2` generates two moving
  curves and advances about0.375m, then fails on unchanged command timeout;
  measured stop and28s video are verified. Stair/person navigation remains
  incomplete. The server remains shut down; original Isaac A4 stays open.
  Status through v188 (2026-10-13; [version index](2026-09-26_newton_stair_reproduction/versions/README.md),
  [archive brief](../handoffs/2026-10-13_newton_v47_v188_archive/SESSION_SUMMARY.md)):
  v47–v85 did not reach sustained 30 Hz local planning (best v58/v59
  27.53/26.43 Hz, maxima 659.526/1236.709 ms); v48 stays `current`. v86–v121
  integrate actual Foxy Nav2; v114 arrives once from the original corner start.
  v139 is validated for its declared fixed corner scenario (6/6 vs 5/6). v147 is
  the first original-start full-route arrival (gpu5070ti, 76.883 m; repeats did
  not hold); v160 is the first Mac finish (1/2); v174 passes the Mac gate with
  qualified stop proofs. v177 (gpu5070ti) arrives 5/5 on the original map/start
  with 30 measured-stop handoffs and no falls: declared-scenario repetition only.
  Terminal-capture candidates v185 3/5 and v186 2/5 are rejected and v187 3/5 is
  not accepted; the unchanged v177 binary control arrived 5/5 and the
  unchanged-source v188 rebuild 3/5, so the cause of the variation is open.
  30 Hz, tails, zero-command drift, other maps, Jetson, robot and VLA
  integration remain unvalidated.

- [`2026-09-23_scan_reactive_stair/`](../handoffs/2026-09-26_scan_stair_handoff.md)
  — Sequential native SCAN stair/observed-person repairs. Old corrected input
  retains one accepted curve through scan32; fresh input still has zero moving
  curves. scan33 reference-target/prefix policy passes15 native cases locally
  and in Foxy, independent code review and full build. Installation identity,
  actual optimizer replay and live qualification are pending after user-reported
  server shutdown. Latest real scan28 video records standing, not stair success.
  [未门控] Main-session archival under inline mode; external archive gate unrun.

- [`2026-09-16_pi_cortex_harnessvln/stance_hold_qualification/`](2026-09-16_pi_cortex_harnessvln/stance_hold_qualification/RESULT.md)
  — Isaac runner PD stance hold (task `.trellis/tasks/archive/2026-09/09-17-isaac-runner-stance-hold/`), Isaac Lab on
  gpu5070ti with V12 `model_149999.pt`; selected entry `xfade1s`. 60 s stand in FIXED_STAND: yaw rate
  ≤ 0.0038 rad/s, drift 2.5 mm (hold off 0.143 rad/s, 3.4 cm). Walk entries ≤ 0.087 rad/s (limit 0.15).
  Two-goal series 8/8 on the unchanged 41 checks (one-sided 95 % lower bound 0.688; hold-off 7/8, 0.529).
  The hold does not change the stop check (still-window median 0.120 vs 0.121 rad/s; all peaks in
  STAND_SETTLING); restart median 0.165 vs 0.201 rad/s. AC7 passes only under Dr Sun's post-result
  amendment D7 (window ends at the restart); as frozen it fails in episode 6 (0.174 rad/s; amended 0.063).
  Thresholds `34c15fe6…`; launchers default to `--stance-hold auto` (D8). Label: integrated, not
  validated; simulation only. Commits `02e4e55b`, `a826eb75`, `87f3c0d1`, `fe82a471`.

- [`2026-09-16_pi_cortex_harnessvln/`](2026-09-16_pi_cortex_harnessvln/README.md)
  — Pi fixture loop and a separate native PCT/SCAN/Lite3 V12 Isaac service;
  one continuous cancel/resubmit/two-goal pilot passed 41 checks, but three
  later display trials failed resubmission, including display off. NVIDIA RViz
  and NVENC display/recording passed; one 45-second simulation comparison showed
  +2.786% physics wall time and +363 MiB sampled active GPU memory, with zero
  telemetry drops. Native SCAN replay traced the rejection to the last-sample
  acceleration being used as the terminal derivative. A one-line isolated
  candidate passed 12/12 fixture calls without relaxing the 1.5 m/s^2 gate;
  Dr Sun adopted it as `scan_04` on 2026-09-17 (PRD D14; Isaac series
  7/8, see `scan_fix_qualification/RESULT.md`).
  See the [local archival handoff](../handoffs/2026-09-16_harnessvln_local_archive.md)
  for immutable run IDs, raw evidence, claim limits and continuation. The
  overall task remains in progress; archive review is pending.

- [`2026-09-10_x_navdp_lite3_rented4090/`](2026-09-10_x_navdp_lite3_rented4090/README.md)
  — X-NavDP posttrain FP32 on RTX 4090 with physical MuJoCo Lite3/model_149999:
  four numeric point-goal trials passed the external 0.25 m arrival criterion;
  both blocked-route trials went around the box with zero detected contacts.
  Videos and raw RGB-D/trajectory records returned locally. No language, exact
  distance, official benchmark, or real-robot validation claim. LightNav runtime
  copies retired on three hosts with historical evidence preserved.

- [`2026-09-09_lightnav0_5070ti_inference/`](2026-09-09_lightnav0_5070ti_inference/RESULT.md)
  — Original LightNav-0 BF16 on RTX 5070 Ti: nine open-loop replay predictions
  passed; sampled total-card peak 12.3502 GiB, warmed 64-observation call median
  192.5 ms. All returned artifact hashes match. No FP8, simulator or robot claim.

- [`2026-09-09_lightnav0_official_demo_rented4090/`](2026-09-09_lightnav0_official_demo_rented4090/README.md)
  — LightNav-0 official MuJoCo demo on rented4090, round 1 executed by Opus:
  pinned BF16 checkpoint served by vLLM, three closed-loop runs through the
  official client and MPC, native model stop in 3/3 (`reproduced` for the demo
  loop). Lead review: all three stopped next to a dog bed 2.3-2.6 m short of the
  instructed trashcan (0/3 arrival); third-person videos, analysis and manifests
  pending in the correction round. Not a paper-score or Lite3 claim.
  Current manual continuation: [visual package v3](2026-09-09_lightnav0_official_demo_rented4090/continuation_v3/EXECUTION_PACKAGE.md),
  prepared after source/host/checkpoint checks and a static orthographic-render probe;
  no new policy episodes or Opus dispatch during this preparation.

> [待核查] Automated archive gate lacked the host/import context and did not
> complete successfully. Local source hashes and the saved SSH snapshot verify
> these facts; manual checks passed, but an automated PASS is not claimed.

- [`2026-08-18_omnivla_offline_smoke/`](2026-08-18_omnivla_offline_smoke/README.md)
  — OmniVLA pinned import (commit `5182600`) and offline inference smoke test.
  OmniVLA-edge: `reproduced` on macOS arm64 / CPU, not the official CUDA
  environment. OmniVLA-original (8B): `imported` at manifest level only, probe
  skipped at the pre-declared memory guard. No Lite3 claim.
- [`2026-08-19_omnivla_original_cuda_gpu40901/`](2026-08-19_omnivla_original_cuda_gpu40901/README.md)
  — pinned OmniVLA-original reproduced for one official-CUDA forward and the
  deployment-specific language-only `move forward` configuration. The broader
  sweep and edge CPU-vs-CUDA comparison remain pending.
- [`2026-08-19_omnivla_lite3_receive_only/`](2026-08-19_omnivla_lite3_receive_only/README.md)
  — Lite3 real front-camera to gpu40901 OmniVLA-original round trip integrated
  and validated for one receive-only request. The server is installed but
  stopped; no locomotion or navigation claim.
- [`2026-09-08_navila_8b_quantized_5070ti/`](2026-09-08_navila_8b_quantized_5070ti/RESULT.md)
  — NaVILA 8B NF4 on RTX 5070 Ti: 11 recorded-image calls plus a fresh-process
  export/reload check passed; peak sampled GPU memory 9,448 MiB and later-call
  median 0.731 s. Initial Chinese straight-ahead requests produced left turns.
  No closed-loop navigation claim; full NF4 payload remains on the execution host.

- [`2026-09-08_dualvln_rented4090/`](2026-09-08_dualvln_rented4090/review/PUBLIC_SCENES_LEAD_REVIEW.md)
  — InternVLA-N1 DualVLN (InternNav `7a5c624`, checkpoint `a698a9e`) in the
  official Habitat evaluator on two frozen custom castle episodes: success
  3/5 and 2/5, all runs on learned STOP. Official R2R subset never ran
  (Matterport3D access). Label: official evaluator on custom public-scene
  tasks, not R2R reproduction.
- [`2026-09-08_dualvln_rented4090/public_scenes/requests/2026-09-10_lite3_camera_ablation/`](2026-09-08_dualvln_rented4090/public_scenes/requests/2026-09-10_lite3_camera_ablation/RESULT.md) Rounds 5/5b/6 (2026-09-11): the real head camera was measured on the robot (+16.7 deg up, HFOV 105), so no crop of it can feed the model; a virtual evaluation camera fused in software from the head camera and the D435i scored 0/10 (c7, level, 6 % uncovered), 2/10 (c8, level, 1.2 %) and 1/10 (c9, 9 deg down, 3.3 %). Dr Sun chose the software-only fusion route on the c8 geometry. Round 6 also showed that episode-1 success measures System 2 route-lock rather than camera geometry at one condition per geometry, which weakens c6 5/10 as evidence too, and that uncovered pixels do not drive System 1 mid-segment stops. 45 runs total; manifest 3,190 files verified both sides; see `review/LEAD_REVIEW.md`.
  — Lite3 camera-condition ablation, 30 supervised runs: baseline 5/10,
  height-only 5/10, FOV-only 3/10, raised 0.65 m mount 2/10, current Lite3
  rig (0.42 m, 20 deg down, D435i FOV) 1/10, head-camera proxy level 2/10,
  head-camera proxy 15 deg down 5/10. Effect sizes on two custom episodes;
  episode 2 fails by stopping late in every wide-FOV condition. Lead review
  recommends the built-in head camera at its existing ~15 deg pitch with a
  software crop to HFOV 79; geometry estimated until measured on the robot.

Before a behavior-changing run, record the parent implementation, motivation,
exact change, expected signals, failure signals, command, local source commit,
and artifact destination. Append results after the run; do not rewrite
pre-run expectations.

- 2026-10-01: [Newton v49 bounded-solve result](2026-09-26_newton_stair_reproduction/versions/v49/RESULTS.md) — rejected: 3.825 Hz attempts /2.883 Hz new plans, max37.998 ms, no >=100 ms tails, timeout reason ignored by backend gate; raw artifacts returned and verified. [Time-series comparison](2026-09-26_newton_stair_reproduction/versions/v49/analysis/time_series/v48_v49_planning_time_series.png).

- 2026-10-01: [v50 upfront-search performance result](2026-09-26_newton_stair_reproduction/versions/v50/RESULTS.md) — frozen directly from v48; build and component safety tests pass, paired replay max107.481→4.827ms with exact geometry. Live maxima1829.626/858.031ms and long corridor stalls fail tail/continuity/30Hz acceptance; v48 remains the experimental reference. Includes a fresh unchanged-v48 control and disclosed v50 trial02 transfer overlap. [All-run time series](2026-09-26_newton_stair_reproduction/versions/v50/analysis/v48_v50_time_series.png).

- 2026-10-01: [Newton v51 artifact storage](2026-09-26_newton_stair_reproduction/versions/v51/RESULTS.md) —62,371 redundant PNGs removed after full verification;152 closed logs compressed byte-exactly;10,260 raw members archived losslessly. About27 GiB free versus948 MiB initially. New renders stream to MP4 with three previews; managed post-run retention and21 tests pass. Navigation remains v48; no new physics.

- 2026-10-02: [Newton v57 two-run validation](2026-09-26_newton_stair_reproduction/versions/v57/RESULTS.md) — old corner passed, 46.20/46.62 m paths without pauses over one second; successful planning25.65/25.76Hz, maximum660.975/290.149ms. Strict30Hz and tail elimination remain unmet. Verified plots and one8.4MiB review MP4 delivered; raw data stays on gpu5070ti.
