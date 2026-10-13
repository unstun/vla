# Stop/hold source inspection

Purpose: inspect the locomotion half of v177's observed zero-command drift.
Status: surveyed only. No source, policy, gains or controller from this directory
was incorporated into execution. No upstream training or deployment was run.

Each `source/*/metadata.json` records the canonical repository, default branch,
commit and repository license metadata; `files.json` records exact selected-file
URLs, sizes and SHA-256. Preserve per-file license notices, especially where
GitHub does not infer a single repository SPDX license.

- DeepRoboticsLab/sdk_deploy at `9ea6ee94bfe90c9a36f5799d39f8dc1d821128db`:
  Lite3 standup state, RL state and policy command conversion.
- unitreerobotics/unitree_rl_gym at `276801e46c5d433564f24658bac64f254b7d2d4b`:
  default-joint-position state and separate policy execution in its humanoid
  deployment example; not a Lite3 stair-hold qualification.
- leggedrobotics/legged_gym at `8fa29acc6fd1910c3d9659eef6310bdd301cde0a`:
  velocity and optional stand-still reward functions; not hard stopping logic.

See `.pipeline/survey/2026-10-12_v177_stop_recovery_upstream_survey.md` for the
combined13repository comparison and the exact applicability limits.
