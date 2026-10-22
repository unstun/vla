# Complete Hook-Free VLA Harness — 2026-10-22

VLA now matches machine-dog's project-hook layout: Claude settings contain no
hooks; Cursor/Codex hook configuration files and all three hook-script
folders are removed. The 21 skills and three Trellis agent definitions per
host remain. Their no-hook direct-reading behavior is documented in AGENTS.md,
SKILLS.md, the Codex entry and the harness specification.

## Startup repair and framework adoption

The previously reviewed 0.6.17 framework update is finalized. The only new
runtime patch beyond those reviewed bytes is in `.trellis/scripts/task.py`:
the shared task-start gate honors configured inline dispatch even when other
host directories have seeded empty subagent manifests. Auto/sub-agent mode
still requires curated entries unless its explicit override is supplied.

The new regression test failed before the patch and passes after it. Fifteen
harness tests pass, including auto-mode rejection, curated-context startup and
the explicit override. All twelve earlier review probes now pass. No simulator,
training, real-robot or remote experiment execution was part of these checks.

## Preservation

Exact pre-removal hook sources, including their pending 0.6.17 updates, are
recoverable from `recovery/removed_hook_sources.tar.gz`; file hashes and the
archive hash are recorded in `recovery/manifest.json`. This archive is inactive
source recovery material, outside every skill/hook discovery path.

The five research/retention modifications and 85 existing untracked research
files retain their baseline SHA-256 values. The 24 historical research commits
remain on local/research-unpublished and must not be ancestors of publication.
Global MCP and the installed Trellis package were not changed. Earlier review
records remain unchanged and are superseded by this task's repair results.

## Publication

Commit only the reviewed framework/cleanup paths and this task. Build the
publication on origin/main, verify the exported code tree, then push main and
the maintenance branch with no held research ancestry. The final Git output
identifies the local source commit and independently based publishing commit.
The active primary checkout remains local/research-unpublished.
