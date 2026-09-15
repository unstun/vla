# Decision log: OmniVLA VLA evidence audit

## 2026-08-19 — freeze receive-only counterfactual protocol

Before any new model inference, this audit freezes one shared protocol for
OmniVLA-original and OmniVLA-edge. Each model receives 24 scheduled forwards:
12 language-panel attempts and 12 vision-panel attempts. Every scheduled
attempt receives a unique run ID and must remain in the local denominator as a
validated success record or an explicit retained failure record.

The audit records normalized upstream `8 x 4` trajectories only. It does not
apply Lite3 metric calibration, collision checking, navigation control, or any
robot command. `actuation_enabled` is fixed to `false` in every record.

No scalar threshold is pre-registered as a VLA verdict. Repeat dispersion,
prompt counterfactuals, image counterfactuals, semantic tendencies, and
failures are shown separately for human review. The final classification is
reserved for Dr Sun.

Immediate-stop conditions are identity mismatch, unsafe compute availability,
an actuation dependency, an unretainable malformed/non-finite output, failure
to synchronize evidence locally, or risk to unrelated workloads or protected
Orin content.

