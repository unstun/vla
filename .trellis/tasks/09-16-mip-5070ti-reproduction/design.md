# Preparation design

Local source of truth: `/Users/sun/tongbu/study/phdproject/vla`.
Execution host: `gpu5070ti` (live verified; the historical `gpu5070ti-relay` alias
is absent). Remote root: `/home/sun/vla_exec/2026-09-16_mip_5070ti`.

Pinned upstream source resides locally at
`references/upstream/2026-09-16_mip/source/AgentCanvas` and remotely under
`$REMOTE_ROOT/source/AgentCanvas`. Each host downloads the approved source directly.
Only task-owned setup wrappers, manifests and compatibility patches are authored
in `.pipeline/experiments/2026-09-16_mip_5070ti/`. The remote applies these exact
bytes; patches never remain solely on the server.

Use the existing `/home/sun/miniconda3` executable to create new upstream-named
environments, after verifying neither environment exists. Existing `isaaclab` is
unrelated and must remain untouched. Install scripts must be read before running:
the upstream simulator installer removes its named environment before recreating
it, despite INSTALL.md describing updates in place.

Bare MIP uses an external reasoning model and GPU rendering, not the optional
SmartWay waypoint network. Do not download RxR BERT features, extra benchmark
assets, optional waypoint models or local VLM weights by default. Exact required
resources follow upstream's main-board installation and subsequent import tests.

Record MP3D's official access requirement; do not accept its terms on the user's
behalf or treat a reachable data URL as authorization. The official `rand100`
episodes are included in the selected source and can be materialized independently.

Sync gate: matching upstream commit, wrapper SHA-256 and all patch SHA-256 before
execution; local copies of setup logs and inventories after execution. Large scene
bytes remain on the execution host, with manifest/hash/location and reacquisition
instructions recorded locally. No model API secrets enter logs or repository files.

Verification progresses from source identity to imports, CLI/HTTP interface,
rendering, then an optional separately identified one-episode navigation probe
after model access and data authorization are resolved. A full benchmark is a
later task stage. A fallback public scene is only a compatibility smoke, not R2R.

Resolved decisions and implementation: MP3D access authorized; the original
100-episode split needs ten scenes, fetched as verified ZIP members. The user
selected DeepSeek Harness and deferred credential setup. Use installed npm
`@deepseek-ai/dsh@0.1.5-rc.1` with its saved dependency lock and Node 24.21.0.
Only bare observe/step are model-visible. The task-owned adapter uses the original
MIP driver/evaluator, 512 RGB, 0.25 m/15 degree actions, 500 steps and 2400 seconds;
its `nonstd` label records the changed harness/model and absent DSH turn cap.

Native rendering and a scripted local model endpoint test the full tool/image
chain without a real API call. Compatibility fixes are local wrappers: MCP
1.26.0 pin, rand100 startup, dataset symlink after materialization, and shutdown
on Habitat's owning GL executor. No upstream source edit is required. The final
launcher must preserve failure exit codes and record simulator teardown status.
