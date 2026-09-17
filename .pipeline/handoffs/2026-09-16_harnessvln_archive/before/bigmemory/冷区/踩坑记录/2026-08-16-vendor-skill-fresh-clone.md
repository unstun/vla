---
origin: human_directed
reviewed: false
date: 2026-08-16
---

# Vendor Skill Fresh-Clone False Dirty State

## Context

`sync-skills.sh` must reconstruct the ignored `.skills-upstream/` checkout from
`vendor-skills.lock` in a fresh clone before rebuilding Skill discovery links.

## Symptom

The first fresh-clone smoke aborted at the Vendor dirty-check immediately after
cloning, even though no user had edited the new Vendor checkout.

## Verified Root Cause

The initial implementation used `git clone --no-checkout`. That creates the Git
metadata and index without materializing the tracked worktree. In this state,
`git status --porcelain` reports the tracked paths as deleted, so the script's
intentional fail-closed dirty-check correctly rejected the checkout.

This was not a real user modification and was not caused by the pinned Vendor
commit.

## Fix

Clone with `--filter=blob:none` while materializing the default worktree, run
the dirty and origin checks on that clean checkout, then switch to the exact
lock-file commit in detached mode. Keep the dirty-check; do not weaken it to
accommodate the artificial `--no-checkout` state.

## Verification

- A temporary fresh project clone completed `./sync-skills.sh` and resolved
  `.skills-upstream` to
  `66f92b61f5b1434a1c7422f6fbd8efc5ee0c0214`.
- Re-running synchronization remained successful and kept generated links
  reproducible.
- Separate wrong-origin and genuinely dirty-checkout cases still failed closed
  before links were regenerated.

## Future Rule

When a bootstrap script performs a clean-worktree check immediately after
cloning, its clone mode must first create a status-clean worktree. Test the
actual fresh-clone path, not only an already populated local checkout; otherwise
a reproducibility script can pass locally while failing on its first intended
use.

## Affected Paths

- `sync-skills.sh`
- `vendor-skills.lock`
- `.trellis/spec/harness/project-harness-contract.md`

## Commit

`7b079f0f3258fe0328f4defcd0f79839e67ba089` (`fix: harden migrated
agent harness`).
