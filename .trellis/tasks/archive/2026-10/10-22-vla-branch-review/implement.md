# Plan

1. Capture current Git refs and SHA-256 of the 50 dirty files and existing
   untracked harness/research files.
2. Verify remote cleanup/main ancestry; fast-forward only the cleanup commit.
3. Rename the current branch without a checkout, detach its upstream, disable
   automatic upstream creation and make local main track the published main.
4. Compare the framework update with installed package templates; review changed
   behavior and isolated runtime probes. Check research-document dependencies.
5. Record a path-by-path review and compact validation results. Commit only this
   task's instructions/report, apply that exact change to the publishable main
   tree using a separate temporary Git index, and verify remote publication.
6. Confirm unpublished ancestry is absent remotely and existing work is unchanged.

No changes to the 50 reviewed files, research records, raw data, global MCP,
global Git configuration, or installed Trellis package.
