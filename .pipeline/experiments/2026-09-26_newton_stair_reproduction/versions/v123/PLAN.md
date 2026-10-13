# gpu5070ti execution port

Stage: experiment + analysis. This is a host port of v122 (candidate) and v116
(control with v114 native code), not MPPI adaptation 2. Keep all frozen parents
unchanged. The behavior gap is that existing launch/build gates assume Mac and
ARM64. Own only x86_64 environment, export/build, launch paths and receipts.
Preserve original CPU Newton solver, Building corner fixture, policy, sensors,
navigation parameters, stop and input-age gates. Report host changes separately.

Local source of truth: /Users/sun/tongbu/study/phdproject/vla.
Execution/bulk root: gpu5070ti:/data/sun/vla_mppi_20261009.
Sync gate: explicit path allowlist and SHA-256 for every transferred file; verify
source and frozen snapshots before build. Rebuild native x86_64 Foxy binaries;
ARM64 install receipts are not reusable. Pin actual image/package identities.
Return allowlist: source/build/host receipts, test summaries, metrics CSV/JSON,
analysis report and optional reviewed MP4. Expected compact return under 15 MB,
excluding an explicitly generated review video. Raw captures remain remotely.

Run native tests and one independently initialized 90-second control/candidate
pair on the same host. Classify every ordinary planning round and check original
success agreement. Record execution, physical navigation and diagnostic acceptance
separately. Incomplete build or run is not a passed host port or step-1 acceptance.
