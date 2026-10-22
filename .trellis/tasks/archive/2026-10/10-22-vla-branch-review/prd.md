# Align publishing branches and review pending changes

Dr Sun authorized branch alignment followed by review of the 50 pre-existing
tracked modifications. Do not upload the 24 historical research commits or
change research records/experimental data.

Acceptance:
- Fast-forward GitHub main with only the already-tested cleanup commit.
- Preserve the current checkout and unpublished history on a local-only branch.
- Keep local main aligned with GitHub, with no implicit push from the research branch.
- Review all 50 paths; distinguish framework updates from research changes and
  account for related untracked dependencies. Do not modify/stage those files.
- Exercise meaningful Trellis behavior in temporary fixtures, record findings
  and publish only this task's documentation/configuration changes.
- Verify original dirty and untracked research files remain unchanged.
