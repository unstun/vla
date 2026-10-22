# Upstream VLA And Navigation Repositories

External repositories are local reference copies, not project source code.

Use this layout:

```text
references/upstream/YYYY-MM-DD_<topic>/
├── repository_manifest.yaml
├── comparison.md
├── raw_logs/
└── source/
    ├── <repo-a>/
    └── <repo-b>/
```

The `source/` and `raw_logs/` directories are ignored by git. Keep the manifest
and comparison tracked. Each manifest records canonical URL, license, pinned
commit, dependencies, original commands, and evidence status.

Do not describe a clone as reproduced or integrated until the corresponding
runtime evidence exists.

## Source storage

Dr Sun selected the external drive on 2026-10-22. Reference source caches live
under `/Volumes/ModelArchive/vla-references/`, preserving project-relative
paths; local `source` links keep the catalogue and tools working. Keep new
reference clones on that drive as well, with a source link in the dated topic.
Manifests and short evidence stay tracked locally. Two already tracked source
snapshots retain their local working-tree bytes and have external backups.
See the [storage inventory and reconnection instructions](storage/2026-10-22_external/README.md).

## Recent collections

- [2026-10-22: 50 recent repositories and six supplementary references](2026-10-22_recent_navigation_50/comparison.md)
  — Chinese catalogue, pinned source, license and integrity records; imported only.
