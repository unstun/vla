# Experiment Records

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
