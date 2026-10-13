---
origin: ai_only
reviewed: false
---

# VLA Project Terminology

This is a draft terminology baseline. Dr Sun approved the first receive-only
VLA contract; the navigation/locomotion action interface remains undecided.

| Term | Project meaning | Boundary |
|---|---|---|
| VLA | A vision-language-action component studied for Lite3 navigation. | Does not imply end-to-end locomotion or real-robot readiness. |
| navigation baseline | A clean, pinned snapshot selected from `machine-dog-nav`. | No baseline has been selected or imported yet. |
| action representation | The output consumed by the navigation or locomotion layer, such as a waypoint, velocity command, trajectory, or another reviewed interface. | The receive-only contract records an 8x4 `[x, y, hx, hy]` trajectory but does not consume or actuate it; the downstream interface remains undecided. |
| receive-only contract | One explicit Lite3 camera frame and language instruction are sent to the pinned VLA service; Lite3 records the returned trajectory. | No automatic loop, trajectory-to-command conversion, navigation sender, or locomotion actuation. |
| uncalibrated_for_lite3 | The upstream-default 0.1 m waypoint scale is preserved only as metadata. | It must not be treated as a validated Lite3 metric trajectory until calibration passes. |
| surveyed | Primary material or a canonical repository was inspected. | No runtime claim. |
| imported | A pinned source snapshot was brought into `/Users/sun/tongbu/study/phdproject/vla`. | No reproduction or integration claim. |
| reproduced | An original upstream procedure ran with recorded evidence. | Does not prove local integration. |
| integrated | The behavior works inside this repository. | Does not prove the declared acceptance test. |
| validated | The declared project acceptance test passed. | Limited to the recorded test scope. |
| camera condition | A named Habitat sensor configuration (height, forward offset, pitch, HFOV, tilt step) under which the official InternNav evaluator is run; every result is labelled by its condition, and the recorded 1.25 m level camera is condition B0. | Says nothing about the real camera unless the condition is rig-faithful and the physical rig matches it. |
| rig-faithful condition | A camera condition derived from the Lite3 sensor-rig URDF and the default-stance torso height (0.42 m, 0.25 m forward, 20 degrees down, D435i field of view, no look-down tilt). | Models the standing camera only; the walking height dip, vibration, lens distortion, and real depth noise are not modelled. |
| public-scene functional test | An official evaluator run on custom frozen episodes in public Habitat test scenes with the pinned model. | Not a benchmark reproduction; reports effect sizes on custom episodes, never published metrics, and does not promote the evidence label. |
| stance hold (PD 站立保持) | Isaac runner mode that hands the joints from the V12 RL policy to a joint-PD hold (Kp 60 / Kd 1, torque-matched target) when the command is exactly zero and the body is quiet on four loaded, balanced feet: RL → STAND_SETTLING → STAND_TRANSITION → FIXED_STAND. Any non-zero command cancels the settle or starts REJOIN (0.25 s blend back to Kp 20 / Kd 0.5). | Simulation only (task `09-17-isaac-runner-stance-hold`, label integrated); not a `machine-dog` deployment or real-robot result. |
| crossfade entry (`xfade1s`) | The selected stance-hold entry (PRD D6): over T_x = 1.0 s the applied PD command blends V12's live PD command into the hold command with weight smoothstep(t / T_x), with Kd 1.0 from entry. `xfade2s` uses T_x = 2.0 s. Resolved by default under `--stance-hold auto` (D8). | Qualified on one flat two-goal route and one scripted walk; its entry-smoothness pass (AC7) rests on a post-result amendment. |
| post-result amendment | A change to an acceptance rule made after the results it scores were known, such as PRD D7 (the AC7 entry window ends at a restart). Reports give both the as-frozen and the amended verdict. | In the stance-hold task a pass resting on it kept the label at integrated, not validated. |
| measured-stop proof (measured-stop handoff) | Newton/Nav2 gateway record that the robot physically stopped before recovery hands the route to a replacement local-trajectory owner: one continuous 1 s window within the original limits of 0.01 command norm, 0.1 m/s horizontal speed and 0.15 rad/s yaw rate (wait budget 10 s since v129). A handoff is one replacement owner admitted after such a proof, as counted in v174–v177 results. | A zero command alone is not a proof. The proof does not show that the pose then stays fixed: v177 run01 moved 0.957 m under effective zero command. Simulation only. |
| terminal crawl (endpoint-crawl criterion) | After the accepted local curve has expired, the controller keeps sending the RL policy a nonzero horizontal correction below 0.1 m/s while the remaining XY error to the curve endpoint is under 5 cm. The prospective v184 criterion, applied to v185–v188 and the v177 06–10 control, flags such an interval longer than 2 s, measured on actual policy-input frames. | Separate from arrival, from the mission-goal tolerance and from zero-command drift. Normal start-up and in-curve braking are not counted. Curve phase is estimated, not an exact controller-clock replay. |
