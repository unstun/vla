# Implementation

1. Record starting HEAD, harness fingerprints, dirty paths, global configuration
   hashes, and protected-tree metadata outside the repository.
2. Apply concise AGENTS.md, the retained project skills, project-only sync,
   hook registrations, and harness documentation. Remove clean retired files.
3. Test synchronization in temporary workspaces, including paths with spaces,
   real-directory collisions, dangling links, vendor links, and repeated runs.
4. Run synchronization in this repository; validate skill frontmatter, discovery,
   configs, Python and shell syntax, and the task context manifests.
5. Compare baseline fingerprints and protected-tree metadata, review this task's
   diff, and record results here. Leave changes uncommitted for review; never
   stage unrelated work. Archive only this maintenance task without a commit.

Rollback: use the recorded starting commit to recover selected retired files
and this task's change list to reverse only the cleanup. Never reset the whole
working tree. The pre-edit fingerprint file is
/private/tmp/vla-harness-cleanup-20261022/before.json.
