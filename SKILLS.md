# Project And Vendor Skills

This repository has two Skill sources:

1. Project-owned Skills are real tracked directories in `.agents/skills/`.
2. Matt Pocock's promoted Skills come from the ignored checkout
   `.skills-upstream/` at the exact revision in `vendor-skills.lock`.

`sync-skills.sh` restores the locked Vendor checkout and builds discovery links
without replacing any real project or platform directory.

## Discovery Layout

| Host | Project Skills | Vendor Skills |
|---|---|---|
| Codex and Agent-Skills hosts | `.agents/skills/` real directories | `.agents/skills/` generated links |
| Claude Code | `.claude/skills/` generated or tracked links | `.claude/skills/` generated links |
| Cursor | `.cursor/skills/` generated links plus Trellis-managed real directories | `.cursor/skills/` generated links |

Project-owned Skills always win on a name collision. Claude Code keeps its
built-in `/code-review`; Codex and Cursor receive the Vendor version.

## Fresh Clone Or Repair

Run from the repository root:

```bash
./sync-skills.sh
```

The script:

- clones the canonical Vendor repository when missing;
- rejects a wrong origin or dirty Vendor checkout;
- checks out the full locked commit in detached mode;
- mirrors project-owned Skills to Claude Code and Cursor;
- links the promoted Vendor set into all three discovery locations.

Restart the host after synchronization so it re-scans project Skills.

## Updating The Vendor Pin

Do not run `git pull` as an update mechanism. Update only through a reviewed
Harness change:

1. Fetch and inspect the upstream history:

   ```bash
   git -C .skills-upstream fetch origin
   git -C .skills-upstream log --oneline --decorate -20 origin/main
   ```

2. Review the new promoted manifest and affected Skill content.
3. Change `vendor.commit` in `vendor-skills.lock` to the selected full commit.
4. Run `./sync-skills.sh` and the Harness validation suite.
5. Commit the lock-file change with its review evidence.

## Project Setup Skill

This project provides a safe project-owned `setup-matt-pocock-skills` override.
It may verify or update `docs/agents/` after Dr Sun approves a tracker change,
but it must never edit the single-line `CLAUDE.md` wrapper and must not create
issues or labels while the VLA repository has no approved remote.

The repository is already configured for local use; setup is not a required
first-run step.

## Notes

- Vendor links and `.skills-upstream/` are generated and intentionally ignored;
  `vendor-skills.lock` and `sync-skills.sh` are the reproducible source.
- Skills marked `disable-model-invocation: true` may be human-only in Claude
  Code; other hosts may not honor that field.
- Host-level discovery is distinct from file-level readiness. If a host changes
  its Skill discovery behavior, verify it live before claiming compatibility.
