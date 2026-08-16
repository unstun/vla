# Design: Harden Migrated Agent Harness

## Boundaries

- Treat `/Users/sun/vla` as the only writable project.
- Treat `machine-dog-nav` and all Vendor repositories as read-only inputs.
- Change only Harness, Skill, state, and verification files; do not import VLA
  implementation code.

## Active Specs

Replace the source-specific backend quality document with a compact pre-baseline
contract. Keep unpopulated backend/frontend files as deferred placeholders and
label them honestly in their indexes. The harness contract remains active and
adds artifact/pinning assertions.

## Artifact Policy

Remove global extension ignores inherited from CAD work. Generated or large
bytes may be local-only only through a reviewed, dated, path-specific ignore
entry accompanied by tracked metadata, provenance, and a digest. This preserves
visibility of new evidence without forcing every large artifact into Git.

## Skill Model

Keep `.agents/skills/` canonical for project-owned Skills. Generate platform
links into `.claude/skills/` and `.cursor/skills/` without replacing real
platform-managed directories. Generate Vendor links into all three discovery
locations from a locked upstream checkout.

Create a project-owned `setup-matt-pocock-skills` override. It verifies existing
repo configuration but cannot modify `CLAUDE.md` or create tracker state before
an approved remote exists.

## Vendor Lock

Track `vendor-skills.lock` using Git-config syntax with canonical URL and exact
commit. `sync-skills.sh` clones when missing, rejects dirty or wrong-origin
checkouts, ensures the commit exists, checks it out detached, and then rebuilds
links. Updating the pin requires a reviewed lock-file change.

## Verification

Validate the proposed tree before commit, including a temporary fresh clone
with the staged patch applied. Verify exact Vendor HEAD, link resolution,
project Skill discovery, strict validation of rewritten Skills, and all existing
Harness syntax/Hook checks.
