# PRD: Audit OmniVLA vision-language-action evidence

## Goal and user value

Give Dr Sun a reproducible evidence pack for deciding whether the two deployed
OmniVLA candidates materially use vision and language to produce an
action-level local trajectory. The task makes the evidence easy to inspect but
does not let an AI make the final VLA classification.

## Background and confirmed facts

- Pinned OmniVLA-original completed a real Lite3-image plus `move forward`
  receive-only forward on `gpu40901` and returned a finite `8 x 4` trajectory.
- Pinned OmniVLA-edge completed a receive-only CUDA forward on the Jetson AGX
  Orin 64GB using the same retained real Lite3 frame.
- Neither single forward establishes language sensitivity, vision sensitivity,
  semantic planning, collision avoidance, metric Lite3 scale, or safe action.
- The local survey records an upstream issue that language prompts may not
  change behavior, so the missing counterfactual evidence is material rather
  than cosmetic.
- Dr Sun requires raw evidence for human review and does not accept the model's
  or an AI reviewer's label as the final answer.

## Requirements

### R1. Fixed identities

- Pin source, checkpoint, preprocessing, modality, and action-head identities
  for OmniVLA-original and OmniVLA-edge.
- Hash every frozen or deterministically derived image and preserve the exact
  prompt bytes and model prompt wrapper.

### R2. Code-path evidence

- Trace image bytes and instruction text through each pinned model path to the
  returned trajectory, citing exact local file/line anchors.
- Identify modality selection/fusion and distinguish code connectivity from
  observed learned sensitivity.

### R3. Counterfactual evidence

- Use the exact 24-attempt matrix per model in `design.md`.
- Compare same-image/different-instruction and different-image/same-instruction
  panels, including forward, left, right, and stop-like prompts.
- Run same-input repeats to establish the model's own repeat variability before
  interpreting counterfactual differences.
- Preserve every attempt, including insensitive, malformed, non-finite,
  nonsensical, timed-out, or semantically inconsistent outputs.

### R4. Review artifact

- Present raw JSON, source/output hashes, input images, trajectory overlays,
  repeat variability, counterfactual metrics, code trace, and claim matrix in a
  compact static local review page.
- Make failed cases at least as visible as successful cases.
- Leave the human decision unselected: `sufficient evidence`, `insufficient
  evidence`, or `revise and rerun`.

### R5. Safety and reproducibility

- Keep all runs receive-only with no robot-control dependency or sender.
- Use task-owned remote paths, bounded timeouts, and pre/postflight checks.
- Synchronize all final code, logs, records, images, and manifests to the local
  source-of-truth repository and prove hashes before any runtime claim.
- Do not modify pristine upstream source, sibling repositories, robot/handheld
  state, network/camera configuration, or protected Orin vehicle content.

## Acceptance criteria

- [ ] AC1: Both models have verified source/checkpoint identities and complete
      code traces from visual/language inputs to `8 x 4` trajectory output.
- [ ] AC2: All 48 planned attempts appear in the local evidence set as either a
      valid output or an explicit retained failure; none are silently dropped.
- [ ] AC3: One versioned validator owns the run-record contract, rejects wrong
      identities/shapes/non-finite values, and remains the source for analysis
      and review rendering.
- [ ] AC4: Raw and summarized results distinguish repeat dispersion from
      prompt/image counterfactual differences for each model.
- [ ] AC5: A visible failure gallery and semantic observations expose prompt
      insensitivity, image insensitivity, left/right inconsistency, and stop
      behavior without converting them into an AI-selected final verdict.
- [ ] AC6: Targeted tests and the existing receive-only suite pass, static scans
      find no actuation dependency, remote task processes are stopped, and all
      retained local/remote hashes agree.
- [ ] AC7: `review/index.html`, raw data, README, decision log, source manifest,
      commands, and logs are locally present and reproducible.
- [ ] AC8: The implementing agent stops without committing or archiving; the
      primary window independently reviews the diff and evidence before Dr Sun
      records a decision.

## Key decisions

- Audit both candidates with one shared protocol rather than treating original
  and edge as equivalent implementations.
- Use a frozen counterfactual batch rather than one favorable example.
- Keep trajectory output normalized and visibly uncalibrated for Lite3.
- Reserve the final VLA classification for Dr Sun.

## Out of scope

- Benchmark-level navigation success, trajectory metric calibration, obstacle
  avoidance, training/fine-tuning, latency benchmarking, APK/control work,
  locomotion integration, or any real-robot motion.
