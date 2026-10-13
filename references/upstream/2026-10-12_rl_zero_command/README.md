# RL zero-command stopping source inspection

Stage: experiment + analysis; status: surveyed only.

Seven upstream repositories and the current checkpoint-bound local source were inspected.
No downloaded source was executed and no policy or controller was changed.

- [Comparison and revised diagnostic plan](../../../.pipeline/survey/2026-10-12_rl_zero_command_upstream_survey.md)
- [Pinned inventory](repository_manifest.yaml) (JSON-compatible YAML)
- [Local V12 source evidence](local_v12_source_evidence.json)
- [Integrity receipt](verification.json)

The five new source snapshots contain selected text, not runnable checkouts.
Two earlier reference snapshots are reused; the legged_gym base configuration
was additionally fetched at its existing pin. Source files remain read-only
reference material. Per-file canonical URLs and SHA-256 values support recovery.
