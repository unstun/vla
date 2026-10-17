# Published Building static background for tracker repair

Stage: experiment and analysis. This imports a hash-pinned static environment
asset for the sequential stair-tracker repair authorized by Dr Sun. It is not
an import of the sibling repository's working implementation.

- Publisher: `Robot-Nav/legbot_3D_Nav`.
- Upstream commit: `f60606a4903bad58fca813f76072f9940a284d1d`.
- File: `src/PCT_planner/src/pcd/building2_9.pcd`.
- Original bytes: 48,000,221; points: 2,000,000 (binary x/y/z and normals).
- SHA-256: `8721efeb74415336d47c97d861d6e30ad213669b120d5b37c62461100c1f2eae`.
- Local authoritative bytes: `source/building2_9.pcd` in this dated directory.
- Acquisition is from the existing verified local upstream cache. Its host
  checkout is `machine-dog-nav`, branch `codex/scan-foxy-isaac`, HEAD
  `848b4aecd01237805e0564c88d3ba09146fd2353`; that checkout is transport context,
  not the source pin. No sibling implementation or working changes are used.
- Repository license text is preserved as `UPSTREAM_LICENSE`; the Building
  asset does not carry a separately identified license. Do not relabel the
  asset as definitively Apache-2.0 merely from the repository license.

The data uses the upstream raw Building frame, aligned with the current VLA
Building mesh and PCT map. Do not apply the source SDF link's extra z=-0.1 m
offset. The copied historical geometry audit is evidence of pairing, not a
replacement for current recorded-cloud alignment checks.

Intended use is a static-background prior to select **tracking candidates**
from actual current LiDAR returns. It must not remove points from SCAN's raw
obstacle cloud, clear unknown occupancy, synthesize human points, or provide
actor positions. A candidate requires full-sequence and static-negative
checks before runtime adoption. Missing/changed prior or unsupported current
foreground must fail closed.

Regeneration URL (pinned Git LFS bytes):

https://media.githubusercontent.com/media/Robot-Nav/legbot_3D_Nav/f60606a4903bad58fca813f76072f9940a284d1d/src/PCT_planner/src/pcd/building2_9.pcd

Fetch those bytes to the local `source/building2_9.pcd`, then verify the exact
size and SHA-256 above before parsing. `asset_manifest.json` pins the copied
metadata and file. Runtime packages copy verified local assets; they never
read the sibling checkout. The existing `references/upstream/.gitignore`
source rule is supplemented by this directory's explicit path-specific rule;
the source URL, hashes, notices and repair evidence remain visible.
