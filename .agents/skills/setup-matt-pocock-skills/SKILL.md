---
name: setup-matt-pocock-skills
description: Verify or deliberately update this VLA repository's issue-tracker, triage-label, and domain-document settings for the Matt Pocock engineering Skills. Use only when Dr Sun asks to configure or change those integrations; preserve the project instruction wrappers and block external writes until a VLA remote is approved.
---

# Safe Engineering-Skill Setup

Verify the existing project configuration before proposing any change.

## Read First

- `AGENTS.md`
- `CLAUDE.md`
- `docs/agents/issue-tracker.md`
- `docs/agents/triage-labels.md`
- `docs/agents/domain.md`
- `git remote -v`

## Immutable Boundaries

- Keep `CLAUDE.md` exactly as the single line `@AGENTS.md`.
- Do not append an Agent-Skills block to `CLAUDE.md`.
- Do not create, label, edit, or close an issue until Dr Sun approves a VLA
  remote and `docs/agents/issue-tracker.md` records it.
- Never fall through to the `machine-dog-nav` remote or tracker.
- Do not create a remote, repository, labels, ADRs, or domain contexts merely
  because they are missing.

## Verification Flow

1. Confirm whether a VLA remote exists and matches the tracker document.
2. Confirm the five triage-role mappings in `docs/agents/triage-labels.md`.
3. Confirm whether the project is single-context, multi-context, or not yet
   modeled; preserve the current state unless Dr Sun asks to change it.
4. Report mismatches and the exact files that would change.
5. Obtain Dr Sun's approval before changing tracker or label configuration.

## Allowed Writes

After explicit approval, edit only the relevant files under `docs/agents/` and,
when a durable project behavior rule truly changes, the corresponding section
of `AGENTS.md`. Keep `CLAUDE.md` untouched.

## Validation

- Verify `CLAUDE.md` remains exactly `@AGENTS.md` followed by a newline.
- Verify tracker commands cannot target another repository when no VLA remote
  exists.
- Review the diff and stage only the approved Harness paths.

If the existing configuration already matches the request, report that setup is
complete without writing files.
