# v206 terminal stance diagnosis

Scope: read-only analysis of the existing v206 Linux attempt and v204 Mac
reference. No navigation/locomotion edits, new physical trials, or threshold
tuning. The local audit scripts are the source of truth; execute them on
gpu5070ti after SHA-256 synchronization and return compact evidence only.

## Ranked hypotheses and falsifiers

1. The support-share gate blocks an otherwise quiet stop. Replay the recorded
   control inputs through the executed StanceHold class. Predict matching
   support-balance rejections; removing only that predicate in an isolated
   counterfactual should reach transition on the same recorded inputs.
2. Residual commands or stale transport repeatedly cancel settling. Predict
   nonzero effective commands or stale transport inside the final wait.
3. The new slew limiter consumes the terminal deadline. Predict delayed command
   zeroing relative to the beginning of the ten-second terminal interval.
4. Stance implementation or platform differences explain the version contrast.
   Compare executed source hashes, sensor path, timing and the v204 terminal
   inputs. Equal source does not imply equal physical trajectories; Mac versus
   Linux is not a controlled version experiment.

## Replay boundary

Telemetry is written after one 20 ms control interval. Its stance mode and foot
forces belong to the update at the preceding row's physical time; body motion
for that update comes from the preceding row. The current effective command is
the command passed to that update. Validate every reconstructed mode, reason
and progress against the recording. This is a decision replay, not a physics
rerun or a claim about the stability of a counterfactual PD transfer.

Expected outputs: source receipts, terminal timeline, per-window force shares,
decision replay equality, one-variable predicate probes, baseline comparison,
and a diagnosis separating direct cause from unproven physical attribution.
