# v206 provenance

Local source of truth: this version, derived from frozen v204. Display-only
v205 remains preserved. Runtime source is composed by materialize_components.py
from the hash-verified v196/v198-v204 chain, then this controller overlay.
The inherited tracking_provenance.json describes the original v82 extraction;
v206's explicitly authorized deviations are listed in PLAN.md and changes.patch.

Execution copy: /data/sun/vla_mppi_20261009/command_continuity_v206_20261015
Host: gpu5070ti, Linux x86_64. No Mac compilation and no physics execution.
Docker image: vla-mppi-foxy:v123-deps03
Image identity: sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4

300 composed source files matched their inventory before execution and after
copyback. The receipt includes installed Tracker/SCAN libraries and the actual
ControllerServer executable, SHA-256, ELF architecture, and resolved dependencies.
14 packages were rebuilt from the composed source, including native dependencies.
The existing dependency tree and OSQP install were mounted read-only.

533 predecessor source/manifest entries and the v205 review MP4 remain unchanged.
All returned evidence files match the remote SHA-256 return manifest.
No remote-only source edits were made. No Git commit or model/policy update.
