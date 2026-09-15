# PRD: Validate OmniVLA trajectory safety offline

## Goal

Determine, from preserved success and failure cases, whether OmniVLA
trajectories are geometrically usable after calibration and independent safety
checking, before any trajectory is allowed to command Lite3.

## Requirements

- Calibrate image geometry, camera-to-body transform, trajectory frame, metric
  scale, and time parameterization.
- Build a sanitizer for shape, finite values, age, length, curvature, continuity,
  body-command envelope, and collision intersection.
- Evaluate controlled scenes containing clear paths, walls, near obstacles,
  ambiguous passages, contradictory instructions, and stop requests.
- Report collision-free rate, instruction compliance, progress, smoothness,
  invalid/rejected rate, and expected intervention count.
- Preserve failure examples and visually overlay trajectory and safety verdict.

## Acceptance criteria

- [ ] Calibration artifacts and assumptions are reviewable and versioned.
- [ ] Every recorded case has raw trajectory, overlay, numerical checks, and a
      declared accept/reject reason.
- [ ] A replay or simulator gate passes before stationary live shadow mode.
- [ ] Dr Sun reviews the failure gallery before any motion-stage proposal.

## Out of scope

- Treating OmniVLA as the only obstacle detector or using uncalibrated 0.1 m
  spacing on Lite3.
