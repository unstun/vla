# Preparation result — 2026-09-16

Preparation acceptance passed on `gpu5070ti`. Real DeepSeek authentication and
model-driven navigation have not run; the user will configure the key later.
This is a user-requested MIP DeepSeek Harness extension, not reproduction of
MIP's published Claude/Codex scores and not Lite3 integration.

## Direct evidence

- Local and remote AgentCanvas commits match
  `b2b363af80a010ea9f73a0be9d49bc75555efdef`. The local source manifest covers
  1,971 files. Remote identity, third-party pins and package checks are in
  `setup/runtime_inventory.json`; wrapper hashes are in `setup/runtime_sync.sha256`.
- The server downloaded dependencies directly. Habitat-Sim 0.1.7, Habitat,
  VLN-CE and the server wire stack imported. Both environment `pip check`
  commands passed. Conda explicit manifests and pip freezes are retained.
  No existing `isaaclab` environment was changed.
- MP3D acquisition completed: ten scenes, 40 files, 2,317,251,399 extracted bytes.
  Every selected member passed size, ZIP CRC32 and SHA-256 checks. The unchanged
  rand100 split hash is
  `b563a76dbbdec5da61ee656ccf5e096b62070423e633987fb437ca1003b4fc67`.
- The final launcher smoke is
  `setup/protocol_smoke/scripted_protocol_only_20260916T091821738581Z/`.
  It used the actual DSH CLI and original MCP bridge with real 512 x 512 Habitat
  images. The model endpoint was a local scripted fixture. All five requests
  exposed exactly observe and step; image counts were 0, 1, 1, 2, 2. The driver
  recorded observe x2, step x2, two simulator steps, `stop_called`, DSH exit 0
  and a completed DSH turn. Peak whole-GPU memory sampled for this small smoke
  was 352 MiB; this is not a model inference memory estimate.
- `setup/simulator_20260916T091819Z.log` records NVIDIA RTX 5070 Ti / OpenGL
  4.6 / driver 580.126.09 and complete application shutdown. Exit 143 reflects
  the launcher's intentional SIGTERM after shutdown. The final inventory shows
  no simulator listener on 19200 and no compute process.
- Six local and server unit tests passed: range extraction/traversal,
  partial-range failure, tool allowlist auditing, nested STOP-result parsing,
  and missing-final-event handling. The reused LightNav range-helper regression
  also passed. Python compilation, shell parsing and whitespace checks passed.

The fixture intentionally turns once then stops. Its zero success score and
zero path length are expected fixture outputs and measure no model's ability.
Native observations remain in the final run's `live_0/`.

## Resolved setup failures

1. Historical `gpu5070ti-relay` was absent; current direct `gpu5070ti` SSH was
   verified against the host and GPU before mutation.
2. Original auto-host loads val_unseen before driver selection. A task-owned
   subclass selects rand100 at startup without relabeling or resampling data.
3. Upstream's unbounded MCP requirement installed 2.2.0, whose renamed API broke
   FastMCP. Pinning 1.26.0 restored the bridge; both final pip checks passed.
4. The installed npm DSH headless command predates the source docs' `--json`
   option. A small plugin captures the actual session/event interface instead.
5. Upstream shutdown closed the GL environment on the main thread and aborted
   with `GL::Context::current(): no current context`. Dispatching shutdown to
   the environment executor fixed teardown, as the final smoke demonstrated.

Historical failure logs and setup smoke attempts are retained. MP3D files match
the official archive; partial full-archive bytes remain after switching to the
exact scene subset.

## Remaining gate and replay

The user will export DEEPSEEK_API_KEY on the server, then explicitly run:

```bash
cd /home/sun/vla_exec/2026-09-16_mip_5070ti
bash scripts/run_one_episode.sh --episode 0
```

The script owns its localhost simulator and refuses a busy port. The default
model is deepseek-flash; image input follows the
[official vision interface](https://api-docs.deepseek.com/guides/vision/).
Real account/model access, cost, long-context image retention and navigation
success remain unvalidated. No formal multi-episode evaluation, training,
optional waypoint network or physical-robot action was launched.

Local source of truth: this repository. The remote is an execution copy.
Returned artifacts must pass `setup/returned_artifacts.sha256`; scene bytes stay
on the authorized server with their file-hash manifest. See `README.md` for
pins, compatibility changes, acquisition steps and the `--protocol-smoke` entry.
