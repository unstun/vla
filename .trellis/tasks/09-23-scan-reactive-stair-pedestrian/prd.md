# Reactive stair traversability and tracked pedestrians in SCAN

Stage: experiment and analysis. Parent: `09-16-emos-harnessvln-reimplementation`.

Dr Sun authorized an implementation attempt on 2026-09-23. Pedestrians move and
have current tracks; SCAN must react to updated observations without predicting
pedestrian trajectories. This task does not authorize physical actuation or
formal training.

## Goal

Make a new SCAN candidate that can treat supported stair terrain as traversable
while keeping every currently observed tracked pedestrian as an obstacle. Use
SCAN's existing replanning and emergency-stop behavior for reactive correction.

## Requirements

- Preserve accepted `scan_04`, the pinned `planner.yaml`, and sibling repos.
- ETH `StepFilter` remains a surveyed source until its exact commit, license,
  input contract, and behavior are recorded. Do not call a new heuristic the
  imported ETH algorithm.
- Terrain and tracked-person occupancy have separate provenance. A stair rule
  must not turn a current person collision into free space. Missing or stale
  required inputs must fail closed.
- Pedestrian input carries current observed position, extent, frame, timestamp,
  and identity. No pedestrian velocity extrapolation, trajectory prediction, or
  time-indexed search.
- Use the same conservative obstacle decision in search, optimization, and the
  live trajectory safety check. Keep unknown and out-of-map blocked.
- Full stair treads, including interiors away from nosings, must be represented
  as supported terrain; the existing one-window prototype is insufficient.
- Keep simulator truth separate from planner input and outcome scoring.
- Dr Sun's 2026-09-24 clarification requires an official human asset in the
  Isaac trial. Pin the NVIDIA model and animation provenance. A procedural
  human or hidden capsule must not substitute for the official sensor target.
  Verify that actual ray hits follow the official actor's current pose before
  accepting any moving-person tracking or avoidance result.

## Acceptance criteria

- [x] A1. Local tests show supported tread traversability, tall-box/thin-wall
      rejection, pedestrian precedence over terrain, stale-track failure, and
      no prediction from track velocity.
- [x] A2. A hash-gated new candidate applies only to a copy of `scan_04`;
      source hashes and frozen occupancy parameters remain unchanged.
- [x] A3. The candidate compiles in the pinned Foxy image and logs source
      identity. A passing source-text test alone is insufficient.
- [ ] A4. A bounded Isaac episode with a moving tracked person exercises live
      SCAN correction on stairs, or records the exact missing simulator/input
      dependency. Report contact, fall, route completion or safe yield, and
      sensor-to-correction timing. One episode is integration evidence only.
- [x] A5. The result states which track source was used (sensor derived or
      simulator oracle), and labels `surveyed`, `integrated`, and `validated`
      separately.

Current gate: A4 has exact missing dependencies recorded in `RESULT.md`, but
the requested moving-person stair episode, correction timing, and outcome
scores have not happened. This task remains in progress.

## 2026-09-26 status

Official animated-human and RTX sensor inputs are now recorded in the runtime
experiment, but latest scan28 live trial has zero navigation motion. A4 remains
unmet as a stair correction/motion result. scan33 is compiled and native-tested
only; install identity and complete real-optimizer replay have not run. Dr Sun
reported server shutdown and requested archival; remote work is stopped.
