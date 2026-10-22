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

## Recent collections

- [2026-10-22: 50 recent repositories and six supplementary references](2026-10-22_recent_navigation_50/comparison.md)
  — Chinese catalogue, pinned source, license and integrity records; imported only.
