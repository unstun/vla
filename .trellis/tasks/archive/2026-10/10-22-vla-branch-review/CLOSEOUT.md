# Branch Alignment And Pending-Change Review

Completed under Dr Sun's 2026-10-22 authorization. Research records, experiments,
the 24 unpublished research commits, the 50 existing tracked modifications and
85 related untracked Trellis-area files were preserved.

## Branch result

The previously tested cleanup commit `0ad3dfda5e665aa3c451014c5f289bc9c7ad02a0`
was fast-forwarded into GitHub main from `8316c9af87d8fd6e99cd9075f19c9c90e0fa7d79`.
Local main tracks origin/main. The original checkout was renamed from main to
`local/research-unpublished` with no checkout/reset/stash, retaining the original
HEAD and every working-tree byte. Its upstream was removed. Repository-local
push.default=simple and push.autoSetupRemote=false make plain push stop; the
expected no-upstream failure was verified with --dry-run.

The task's final publication carries only branch instructions and this review
on top of the published main. Local research ancestry is excluded. The exact
final commit/ref verification is reported in the accompanying Git operation.
See `docs/agents/git-workflow.md` for the ongoing two-branch policy.

## Review result

See `REVIEW.md` for one reproduced P2 regression in the pending Trellis 0.6.17
update, the five-file research/retention boundary, and all 50 path dispositions.
The runtime review ran only in temporary fixture repositories: 11 checks pass;
the multi-platform inline-start check fails, while the pre-update version passes.
The existing explicit empty-context override works. This was review, not an
implementation of that fix; none of the 50 files was staged or changed.

The five research/retention edits depend on additional untracked evidence.
All newly linked local files exist. All ten ignored review MP4s match their
storage manifest in byte size and SHA-256, but that manifest is also untracked.
Do not publish those five files in isolation.

## Preservation and scope

SHA-256 checks match all 50 original modifications and 85 untracked Trellis-area
files. The 538,427 protected research/source/data entries match their earlier
metadata snapshot, with no additions, removals or metadata changes. Global MCP,
research indexes, real journals, original experiment tasks, installed Trellis,
training and simulator processes were not changed.

Before adoption of the 45-file framework update, fix or explicitly resolve the
inline-start regression. Research publication remains a separate decision.
