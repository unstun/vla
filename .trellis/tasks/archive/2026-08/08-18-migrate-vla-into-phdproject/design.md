# Design: Complete Repository Path Migration

## Boundary

The migration is a same-volume directory relocation from:

```text
/Users/sun/vla
```

to:

```text
/Users/sun/tongbu/study/phdproject/vla
```

No compatibility symlink will remain at the old path. The destination becomes
the sole VLA source of truth.

## Migration Strategy

1. Capture a pre-move inventory, size, Git HEAD/status, nested-repository state,
   symlink list, and absolute-path occurrence list.
2. Update only live operational documents and task-owned records that must
   resolve against the new root.
3. Review the diff before relocation.
4. Reconfirm the explicit source and destination and that the destination is
   absent.
5. Perform a same-filesystem directory move.
6. Run all validation from the destination path.
7. If structural validation fails, move the directory back to the original
   path before attempting repairs.

## Path Rewrite Policy

Rewrite:

- `AGENTS.md` scope and source-of-truth declarations;
- current hot-memory state files;
- live harness and pipeline documentation;
- active project skills whose instructions point to the old root;
- current non-archival survey documents where the path is an operational link.

Do not rewrite:

- source-conversation captures;
- archived Trellis task records;
- cold historical records describing what was true at that time;
- checksum-bound staging evidence and its manifest;
- Git object history.

Remaining `/Users/sun/vla` occurrences will therefore be classified rather than
blindly replaced.

## Compatibility

- Relative symlinks remain valid because internal directory topology does not
  change.
- The Codex desktop thread may retain the old workspace root after the move;
  Dr Sun must reopen the new directory for future work.
- Large future checkpoints will now reside under the `tongbu` project tree if
  stored inside the repository, so cloud-sync behavior must be reviewed in the
  later OmniVLA task.

## Rollback

Until validation passes, rollback is the inverse explicit move from the new
path to the old path, provided the old path remains absent. No deletion or
recursive cleanup is part of the migration.
