# Implementation plan

Nothing in steps 1–4 stages or commits. Step 5 is the approval gate.

- [x] 1. Snapshot the worktree:
      - SHA-256 of every untracked and modified file, into `review/before.sha256`;
      - the staged Phase A list, into `review/phase_a_staged.txt`.
- [x] 2. Write `classify_backlog.py` (rules from `design.md`) and run it:
      - output `review/classification.json` plus per-group path lists `review/group_01.txt` … `group_10.txt`;
      - stop if any path is unclassified or claimed by two groups.
- [x] 3. Write the local-only records:
      - `LOCAL_ONLY_BYTES.sha256` for each root;
      - append the `.gitignore` blocks;
      - check that `git check-ignore --no-index` returns exactly the `local_only` set.
- [x] 4. Build the review table (`review/REVIEW_TABLE.md`): one row per commit with message, path count, bytes, top
      directories, files over 5 MB and the Dr Sun edits included. Run a trellis-check pass on the script, manifests
      and `.gitignore`.
- [x] 5. **Gate** (approved 2026-09-15, with two small exceptions tracked): show Dr Sun the table and wait for approval, which may come with changes. Changes send us back to
      step 2.
- [x] 6. `git restore --staged` the Phase A list. Confirm the index is empty and those files are still byte-identical.
- [x] 7. For groups 1–10, one at a time (committed 2026-09-15, `ab7c8414`..`7870e9cd`, each checked against its list):
      1. `git add --pathspec-from-file=review/group_NN.txt`;
      2. check that the staged names equal the group list;
      3. run the credential scan on staged text;
      4. parse-check changed JSON, YAML, TOML, Python and shell;
      5. `git commit`, then check that `git show --stat HEAD` matches.
      Before commit 2, re-run the classifier and confirm again that the newly ignored set equals the local-only set,
      so no file created since is ignored without a manifest entry. Group 10 also refreshes the hot zone and journal
      and ticks E.2 in the Isaac task; re-run the classifier to regenerate `group_10.txt` first. Those edits are
      shown to Dr Sun before the commit.
- [x] 8. Final checks (AC1–AC5): the commands below; also `review/after.sha256` equals `before.sha256` for every
      evidence file.
- [x] 9. Report the outcome, including the repository size and the deferred playwright paths.

## Validation commands

    git status --porcelain
    for m in $(git ls-files '*LOCAL_ONLY_BYTES.sha256'); do (cd "$(dirname "$m")" && shasum -a 256 -c --quiet LOCAL_ONLY_BYTES.sha256) || echo "FAIL $m"; done
    git ls-files -z | xargs -0 stat -f '%z %N' | awk '$1>5242880'
    for e in pdf png mp4 zip step; do git check-ignore -v --no-index "docs/research/probe.$e" || echo "not ignored: $e"; done
    printf '@AGENTS.md\n' | cmp - CLAUDE.md
    git count-objects -vH

## Rollback points

- Before step 7, everything is reversible without touching history: delete the new manifests and revert the
  `.gitignore` edits.
- During step 7, a bad commit that has not been built on is undone with `git reset --soft HEAD~1`, and only with
  Dr Sun's approval.

## Notes from execution

- The before-snapshot (`before.sha256`, 34,158 lines) and `local_only.txt` live in the session scratchpad, not here. The
  durable equivalents are the 15 committed `LOCAL_ONLY_BYTES.sha256` manifests.
- The 50 multi-line `progress.json` files under DualVLN `public_scenes/runs/` are upstream JSON Lines; all 101 lines
  across the 51 such files parse. They are left unchanged.
