# Branch design

Rename the checked-out main branch to local/research-unpublished without checking
out files. Remove its upstream and disable automatic upstream creation locally.
Advance GitHub main by the cleanup branch only, then create a local main pointer
at that same commit. Keep the original research history reachable locally.

Publishing work uses main or a new codex/* branch based on origin/main, with
explicitly selected task files. Do not merge the research branch into a published
branch. The existing checkout remains the research source of truth.

Review the pending framework update against the installed 0.6.17 package and
its hash manifest. Run task/journal operations only in temporary fixture repos.
Keep the 50 modifications and related existing untracked research files intact.
