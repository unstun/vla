---
origin: human_directed
reviewed: false
date: 2026-08-18
---

# VLA Repository Path Migration

## Decision

Dr Sun requested a complete physical migration of the VLA repository from
`/Users/sun/vla` to `/Users/sun/tongbu/study/phdproject/vla`. The old path was
not retained as a compatibility symlink.

## Preserved State

- Outer Git HEAD: `59b293c1214ceaad126cb06224156526a837fb99`
- Branch: `main`
- Nested Vendor Skills HEAD: `66f92b61f5b1434a1c7422f6fbd8efc5ee0c0214`
- Directory entries: `1744`
- Regular files: `1130`
- Symlinks: `112`, with zero broken links
- Relative-path inventory SHA-256:
  `4614f9d2391169b955ec862d6998eb221acc2fd8d0f5632b0ffc3a3c18581973`
- Directory size at the move gate: `660364 KiB`
- `CLAUDE.md` SHA-256:
  `336cc4fbf19beaada7ccf9986414fa91851a8d7a07dfb3ccbe800a69eed0ab49`

All values matched before and after the same-volume directory move.

## Path Update Policy

Current operational source-of-truth declarations, active skills, pipeline
documentation, terminology, survey location notes, and hot memory now use the
new path. Historical conversation captures, archived Trellis tasks, prior cold
records, and checksum-bound staging evidence retain `/Users/sun/vla` as a fact
about their original context.

## Verification

- Trellis `0.6.14` context and task validation passed from the new root.
- All project and Vendor Skill links resolve after synchronization.
- Python compilation, shell syntax, Git diff checks, Vendor lock verification,
  `CLAUDE.md` wrapper verification, and Trellis update dry-run passed.
- The old path no longer exists.

## Boundary

This migration did not import OmniVLA source or checkpoints and did not run
inference, training, Isaac Lab, simulation, or real-robot commands.
