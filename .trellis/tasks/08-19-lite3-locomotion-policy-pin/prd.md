# PRD: Pin and integrate the validated Lite3 locomotion policy

## Goal

Keep a known Lite3 locomotion policy as the only low-level controller and expose
a narrow, bounded body-command interface to the future VLA safety layer.

## Requirements

- Use the V12 `model_149999` policy confirmed by Dr Sun on 2026-08-19.
- Pin checkpoint, exported ONNX, training configuration, observation/action
  contract, controller source, and hashes.
- Reuse existing locomotion evidence; do not relabel simulation or historical
  motion as a new validation.
- Verify standalone safe start, zero command, bounded manual command, watchdog,
  damping/handback, and signal shutdown under the selected version.
- Accept only bounded body commands from a separate arbiter; never accept VLA
  joint targets.

## Acceptance criteria

- [x] Dr Sun confirmed V12 `model_149999` as the exact policy identity.
- [ ] A manifest pins every runtime dependency and interface field.
- [ ] Standalone lower-controller verification passes before VLA is connected.
- [ ] The body-command contract has explicit limits, TTL, state prerequisites,
      and safe-stop behavior.

## Out of scope

- Retraining the locomotion policy or changing its reward design.
