# Reuse and scope

Upstream repositories, licenses, commits and original commands remain pinned
by v224/REUSE.md and references/upstream/2026-10-16_pct_scan_origin_audit.
This is a local overlay, not a new upstream import or reproduction claim.

Reuse the existing PCT A*, GTSAM factors/GP interpolators, SCAN cubic spline and
L-BFGS, native physical-floor/ETH evidence, and PCL voxel oracle. Runtime lookup
and explicit derivatives replace repeated PCL searches and finite differences.
PCL is used only by the isolated offline exporter/oracle for this new channel;
the native mapper's existing PCL dependency is retained.

The atlas is single-cylinder XYZ, sampled at continuously rotated centers with
unchanged Z. No yaw bins, per-floor height snapping, contact planner, recovery
state machine, RL change or additional online mapper is introduced.

Regeneration: compose with prepare_workspace.py; run build.sh with a new named
attempt; build tools/CMakeLists.txt in the pinned Docker image; export the atlas
from the frozen v224 ENV field; run prepare_probe.py, atlas_probe, field_probe
and admission_probe. Recorded GPMP diagnostics generate private instrumented
copies only after verifying actual composed source hashes.
