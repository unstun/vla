# Trellis 0.6.15 update

Dr Sun requested the displayed 0.6.14 -> 0.6.15 update during the LightNav GPU
probe. Installed CLI was already 0.6.15. `trellis update --dry-run` identified
29 template updates and four locally modified configuration files.

Executed `trellis update --skip-all`: 29 templates updated; `.trellis/config.yaml`,
`.claude/settings.json`, `.codex/hooks.json`, and `.codex/config.toml` preserved.
Automatic backup: `.trellis/.backup-2026-09-09T17-41-08/`.

Verification: project `.trellis/.version` and CLI both report 0.6.15; all 147
protected source-of-truth, task, spec, journal and configuration files retain
their pre-update SHA-256. `CLAUDE.md` remains exactly `@AGENTS.md` plus newline.
All Python scripts/hooks under the affected roots parse successfully. Current
task still resolves to `09-09-lightnav0-5070ti-inference`.

See `update.log`, `protected_before.json`, `preserved_before/`, and
`verification.json`. The update mentioned npm 0.6.16; this operation applied
the requested installed 0.6.15 version and did not upgrade the global CLI.
