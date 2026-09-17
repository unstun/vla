# Execution record

## 2026-09-16 follow-up: credential and one-episode check

Dr Sun reported the server key configured and said "好了，你试试". This authorizes
checking that configured credential and running the prepared episode 0. Load
`~/.config/mip/deepseek.env` on the server; never return its contents. First test
the configured/default endpoint once. Authentication or routing failure stops
the launch; do not guess alternate providers or send the key to other endpoints.
No formal multi-episode benchmark, training or robot actuation is authorized.

Outcome: official models endpoint returned 200; one real deepseek-flash episode
ran as `nonstd_deepseek_flash_bare_20260916T105741013685Z`. Runtime passed;
navigation success 0/1, oracle 0/1, native STOP at evaluator distance 4.7544 m,
path 6.8723 m, 156 actions, 35 observations, 404.5 seconds. Model self-report of
arrival did not match evaluator scoring. All 56 returned artifacts passed local
hash verification; original-frame replay encoded and decoded successfully.
Eight unit checks passed. Simulator stopped; no further episode was launched.
See `REAL_EPISODE_RESULT.md` for evidence and claim boundaries.

## Preparation record

- [x] Read project constraints, upstream-survey record and remote-experiment specs.
- [x] Verify SSH alias: `gpu5070ti`, direct port 60023; host `ubuntu`, user `sun`.
- [x] Live capacity: RTX 5070 Ti 16,303 MiB, 163 MiB used, no compute process;
      approximately 28 GiB RAM available and 82 GB filesystem space available.
- [x] Confirm existing conda environments are only base and isaaclab.
- [x] Resolve paper branch to `b2b363af80a010ea9f73a0be9d49bc75555efdef`.
- [x] Acquire local pinned source and remote independent download.
- [x] Review all installer dependencies and side effects; prepare task-owned wrapper.
- [x] Install runner and simulator environments with retained logs.
- [x] Materialize the original `rand100` episode and ground-truth files unchanged.
- [x] Record user MP3D authorization; download and verify 10 scenes / 40 files.
- [x] Install DeepSeek Harness 0.1.5-rc.1 and Node 24.21.0; retain dependency lock.
- [x] Implement DeepSeek extension to the original driver, MCP and evaluator.
- [x] Resolve MCP 2 API drift using 1.26.0; both final pip checks pass.
- [x] Resolve rand100 startup and OpenGL thread-affine shutdown in a local wrapper.
- [x] Verify real rendering and DSH -> MCP -> Habitat -> model image request path.
- [x] Exercise full launcher lifecycle with five scripted requests and native STOP.
- [x] Run six unit tests locally/remotely, helper regression, compile/shell checks.
- [x] Return hashes, logs, images, environment inventories and result summary locally.
- [x] User configures server-side DEEPSEEK_API_KEY, then real one-episode model check.

Historical preparation acceptance passed; evidence is in the experiment's `RESULT.md`.
User decisions: MP3D authorized, DeepSeek Harness selected, user will configure
the server key later. There were no unanswered setup questions. At that preparation
boundary there was no real API
request, formal benchmark, training or robot actuation occurred. All model runs
are labeled nonstd; no paper-score reproduction or Lite3 integration is claimed.
Existing Isaac/D.1 work was preserved. No commit or automatic archive was made.
Initial alias check failed for `gpu5070ti-relay`; it no longer matches a configured
host and must not be used. The first live `gpu5070ti` inventory command returned
2 because optional filesystem paths were absent; hostname/GPU checks succeeded.
