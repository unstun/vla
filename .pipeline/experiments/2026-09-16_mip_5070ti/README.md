# MIP preparation on RTX 5070 Ti

Stage: experiment + analysis. Status: preparation checks passed; real DeepSeek
authentication and the first episode completed. Navigation success was 0/1,
with native STOP 4.7544 m from the goal. See `REAL_EPISODE_RESULT.md`.
User selected DeepSeek Harness and confirmed Matterport3D access on 2026-09-16.

Local source of truth: `/Users/sun/tongbu/study/phdproject/vla`.
Execution copy: `gpu5070ti:/home/sun/vla_exec/2026-09-16_mip_5070ti`.
Upstream: `jianzhou0420/AgentCanvas`, paper branch
`archive/mip-embodied-agents-take-control`, commit
`b2b363af80a010ea9f73a0be9d49bc75555efdef`.

The server downloads source, dependencies and data directly. Setup logs and
inventories are returned to `setup/`. Scene bytes remain on the server with
local hash manifests and the original acquisition URL. Compatibility changes
and DeepSeek Harness configuration belong in this directory, not only remotely.

DeepSeek Harness is a user-requested extension to the paper's original harness
matrix. Preserve the MIP observation/action contract and record the exact model,
runtime version, prompt, tool schema and protocol differences before a run.
Do not report this extension as reproduction of the paper's Claude/Codex metrics.

The upstream installers are recorded verbatim. Their version constraints were
developed on RTX 3090; 5070 Ti compatibility requires actual import and rendering
checks. No formal benchmark or physical robot actuation has been started.

## Ready entry on the execution host

The user configured the private key on the server. In a Bash server shell:

```bash
ssh gpu5070ti
cd /home/sun/vla_exec/2026-09-16_mip_5070ti
source ~/.config/mip/deepseek.env
bash scripts/run_one_episode.sh --episode 0
```

The private file exports DEEPSEEK_API_KEY; its value is not copied into project
artifacts. If already exported, only the launch command is needed. The
launcher owns a localhost-only simulator on port 19200, refuses a busy port,
runs exactly one selected episode, and terminates its simulator afterwards.
Outputs go to a fresh `runs/nonstd_deepseek_flash_bare_<UTC>/` directory.
The original preparation made no real API call; the later authorized first
episode and its outcome are recorded in `REAL_EPISODE_RESULT.md`.

To repeat the credential-free interface check:

```bash
bash scripts/run_one_episode.sh --protocol-smoke
```

This uses the installed DeepSeek Harness, original MCP bridge, actual Habitat
scene and rendered RGB. A local scripted endpoint asks for observe, left turn,
observe, STOP and a final answer. Its results belong under `setup/protocol_smoke/`
and must never be counted as model navigation performance.

## Pinned setup and contract

| Item | Prepared value |
| --- | --- |
| MIP / AgentCanvas | `b2b363af80a010ea9f73a0be9d49bc75555efdef` |
| VLN-CE | `5344526b26aa59212117c8ac864deaaf58e930ef` |
| habitat-lab | `d6ed1c0a0e786f16f261de2beafe347f4186d0d8` |
| Habitat-Sim | `0.1.7`, actual NVIDIA EGL rendering checked |
| Runner / simulator | Conda `agentcanvas` Python 3.10 / `ac-vlnce` Python 3.8 |
| DeepSeek Harness | npm `@deepseek-ai/dsh@0.1.5-rc.1`; full dependency lock retained |
| DSH Node runtime | `v24.21.0`, SHA-256 in `setup/node_runtime_pin.json` |
| MCP Python compatibility | `mcp==1.26.0` |
| Model route | `deepseek-official` / `deepseek-flash`, high reasoning, 8,192 output-token cap per request |
| Observation | 512 x 512 RGB; original instruction |
| Tools | `mcp__env__observe`, `mcp__env__step` only; no shell, files, web or subagent tools |
| Actions | 0 STOP, 1 forward 0.25 m, 2 left 15 degrees, 3 right 15 degrees |
| Limits | Original 500 simulator steps and 2,400 seconds; DSH has no additional hard turn cap |
| Data | Unchanged `rand100`: 100 episodes, 10 MP3D scenes, 40 verified scene files |

The README's occasional 30-degree wording differs from the pinned MCP bridge
and VLN-CE task YAML, both of which specify 15 degrees. This preparation keeps
the executable 15-degree contract. DeepSeek supports image input through its
[official vision API](https://api-docs.deepseek.com/guides/vision/). Real account
access and model/tool responses were exercised in the first episode. Billing
was not measured, and a formal navigation benchmark remains unrun.

## Resource acquisition and replay

MP3D access was explicitly confirmed by Dr Sun in `configs/MP3D_AUTHORIZED.txt`.
`scripts/fetch_mp3d_subset.py` reads the original official archive with strict
HTTP range validation, extracts only all files for the ten required scenes, and
checks ZIP CRC32, size and SHA-256. It does not replace or resample any episode.
The selected members total 1,680,013,684 compressed bytes and 2,317,251,399
extracted bytes. Full-archive download was stopped after the exact subset was
identified; its partial file and historical log remain on the host.

The extracted scene data stay at
`source/AgentCanvas/data/habitat/scene_datasets/mp3d/` on the execution host.
`setup/mp3d_subset_plan.json` records the source URL, archive size, split hash,
scene names and members; `setup/mp3d_subset_verified.json` has all 40 file hashes.
The range helper is reused byte-for-byte from the prior LightNav experiment;
its local origin and remote hash are in `setup/runtime_inventory.json`.

After restoring the pinned source and syncing this task's scripts/configs plus
`setup/node_runtime_pin.json` and `setup/dsh_package_lock.json`, setup is:

```bash
bash scripts/bootstrap.sh "$PWD"
bash scripts/install_deepseek.sh "$PWD"
python3 scripts/fetch_mp3d_subset.py "$PWD" \
  --range-helper dependencies/download_assets.py --workers 10
bash scripts/run_one_episode.sh --protocol-smoke
python3 scripts/record_setup.py
```

Copy the recorded LightNav helper to `dependencies/download_assets.py` first.
The initial installers create the upstream-named environments; bootstrap's
markers prevent their destructive reinstall. On another host, inspect existing
environments before the first bootstrap. The saved Conda explicit manifests,
pip freezes and npm lock record the exact tested dependency set; the original
upstream installers alone have floating constraints and may resolve differently.

## Compatibility changes and evidence

- `configs/runner-compat.txt` pins MCP 1.26.0: upstream's unbounded `mcp>=1.0.0`
  installed 2.2.0, which removed `mcp.server.fastmcp`.
- The unchanged upstream installer adds VLN-CE's `setup.py` from its committed
  installer patch, creates its data symlinks and applies the documented ac-vlnce
  OpenGL library/activation-hook setup. The third-party working-tree status is
  recorded separately from the clean AgentCanvas source status.
- `scripts/simulator_nodeset.py` starts on `rand100` instead of the unavailable
  default `val_unseen`. It dispatches shutdown onto Habitat's owning executor;
  upstream shutdown on the main thread aborted with `GL::Context::current()`.
- `scripts/deepseek_adapter.py` plugs into the original MIP driver without editing
  the upstream tree. It preserves the original bridge, episode placement,
  observation/action definitions and evaluator. It labels all model runs `nonstd`.
- The installed DSH headless version lacks the newer source documentation's
  `--json` option. `scripts/dsh_events.mjs` captures its actual session/event API.
  Events, exact prompt and plugin patch are retained per episode. DSH's internal
  image retention and system prompt remain harness-specific experimental factors.

`RESULT.md` records the checks and claim boundary. `setup/protocol_smoke/result.json`
points to the final successful scripted test. The five model requests saw exactly
two tools; image counts were 0, 1, 1, 2, 2. MIP recorded two observations, two
actions, native STOP and DSH exit 0. The simulator then logged complete shutdown
and exited 143 after the launcher's intentional SIGTERM; no process remained.
The fixture's zero success score is expected after a turn and STOP and is not an
evaluation of DeepSeek.

`setup/returned_artifacts.sha256` verifies every returned setup artifact. Large
source bytes use the existing path-specific upstream source ignore; their local
file hashes and reacquisition identity are in
`references/upstream/2026-09-16_mip/source_manifest.json` and
`repository_manifest.yaml`. Scene data are retained on the authorized execution
host. No global ignore pattern, sibling repository, robot interface or policy was
changed. No changes were committed in this task.
