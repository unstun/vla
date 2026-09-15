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
