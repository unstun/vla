# First real DeepSeek episode — 2026-09-16

The configured credential works and the complete model/tool/simulator run
finished without a runtime error. Navigation failed in this one episode:
DeepSeek issued STOP while the evaluator still measured 4.7544 m to the goal,
outside the 3 m success radius. Oracle success was also zero.

This is one exploratory MIP DeepSeek Harness extension run, not reproduction
of the paper's original Claude/Codex scores or validation on Lite3.

## Authorization and identity

Dr Sun configured `~/.config/mip/deepseek.env` on the server and said
"好了，你试试". Only the prepared episode 0 was executed. The server loaded the
credential locally; no credential bytes were found in the returned artifacts.
`setup/api_access_20260916T105636Z.json` records HTTP 200 from the official
`https://api.deepseek.com/models` endpoint and availability of deepseek-flash.

Run: `runs/nonstd_deepseek_flash_bare_20260916T105741013685Z/`.
Model: deepseek-flash through DeepSeek Harness 0.1.5-rc.1, high reasoning,
8,192 output-token cap per request. MIP source:
`b2b363af80a010ea9f73a0be9d49bc75555efdef`.
Dataset: unchanged R2R-CE rand100, index 0, original episode ID 7, scene
`x8F5xyUWy9e`. The instruction asks the agent to pass the pool, walk between
the bar and chairs, and stop at the corner of the bar. No prompt or action
contract was changed during this run.

## Recorded result

| Measure | Result |
| --- | --- |
| Success / oracle success | 0/1 / 0/1 |
| Final evaluator distance to goal | 4.7544 m |
| Actual path length | 6.8723 m |
| SPL / nDTW | 0 / 0.6554 |
| Environment actions | 156: forward 43, left 37, right 75, STOP 1 |
| MCP calls | observe 35, step 35 |
| DSH model loop steps | 71 |
| Episode wall time | 404.5 seconds |
| Stop reason | Native model-issued `stop_called` |
| Harness / launcher exit | 0 / 0 |
| Sampled whole-GPU peak | 386 MiB; external API model, not local VLM memory |

The model's final answer claimed it had reached the bar corner within 3 m.
That self-report disagrees with the evaluator and is not used to score success.
The recorded failure concerns this episode's goal/STOP judgment. One run cannot
establish a model ranking or full benchmark result.

## Evidence and replay

- `summary.json`: original MIP metrics, model usage counters, native STOP and
  harness outcome. `total_cost_usd` is unavailable; no dollar estimate is made.
- `episode_0.jsonl`, `raw/`: original instruction, actual model route/prompt,
  exact plugin patch, model events and tool results. Native raw event timestamps
  carry the interaction timing; the normalized sink replays events at run end.
- `live_0/`: all 35 original 512 x 512 observations and action records.
- `replay_2fps.mp4`: 17.5-second convenience replay, one observation every 0.5 s.
  It is not real-time footage. `replay_manifest.json` records frame count,
  decoding metadata, time basis and video SHA-256.
- `final_inventory.json`: simulator shut down completely, expected SIGTERM exit
  143, no listener on port 19200, no compute process, GPU returned to 195 MiB.
- `remote_artifacts.sha256` and `local_verification.json`: all 56 returned files
  matched their remote hashes. Derived local video has its separate hash.

Eight unit checks passed, including a credential preflight failure/redaction
check and an actual local HTTP redirect test proving no second endpoint is
contacted. The simulator/model outcome above is a real run, not those fixtures.

The private key file remains on the server. Preparation evidence in `RESULT.md`
is retained as history. No further navigation episode, formal benchmark,
training, robot actuation or commit was performed after this one trial.
