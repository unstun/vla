# Pi / Cortex HarnessVLN Integration Results

> Archive update, 2026-09-16: actual4 remains one accepted pilot. Three later
> display-condition runs failed at SCAN resubmission. The endpoint-derivative
> cause and isolated native candidate are verified; production adoption and a
> corrected Isaac episode remain pending. See [current archive](../../handoffs/2026-09-16_harnessvln_local_archive.md).

Date: 2026-09-16. Stage: experiment + analysis.

The latest accepted result is the [P2B continuous native navigation pilot](P2B_RESULT.md):
real PCT/SCAN/V12 in Isaac completes a mid-motion cancel, confirmed stop,
replanning to goal A and arrival at goal B in one 16.52-second simulation
episode. The root checked raw physics, requested-target errors, stop windows,
source identities, video and all 34 returned artifact hashes. This result uses
known-map/truth-pose inputs. Pi-to-real-service integration, actual Cortex,
visual grounding, graph memory, SLAM and language evaluation remain open.

## P1 historical result: offline Pi tool protocol

The result below describes the earlier offline gate, not the later P2B run.

The actual Pi agent-core 0.85.1 loop executes against the project Python
fixture gateway. The same 16 tests passed locally and on the 5070 Ti Linux
execution host. This is protocol evidence, not a navigation benchmark result.

| Evidence | Result |
|---|---|
| Python state/validation tests | 11 passed on each host |
| Real Pi loop/transport tests | 5 passed on each host |
| Scripted provider turns | 10 |
| Fixture executor movement calls | 2 |
| Intended rejections | 3: premature stop, second movement in one response, stale observation |
| Completion evidence | Fresh observation `obs-2` for doorway and `obs-3` for table |
| Native terminal cause | `accepted_fixture_stop` |
| Actual LLM calls / tokens billed by this probe | 0 / 0 |
| Cortex/ROS execution | Not performed |
| Habitat / real sensor / robot execution | Not performed |
| Linux source equality gate | Passed for all transferred source/configuration files |
| Returned evidence | 11 files, all SHA-256 values match |

## Local evidence

- `checks/checks_20260916T132105Z/result.json`: commands and exit codes.
- `checks/checks_20260916T132105Z/source_sha256.json`: tested source hashes.
- `runs/offline_2026-09-16T13-21-06-310Z/result.json`: scripted-run summary.
- Adjacent `trace.json`: actual Pi events, provider inputs and gateway events.

Local runtime: Node v25.9.0. Linux uses the existing pinned MIP-owned Node
v24.21.0 binary read-only, with a separate npm dependency directory and no
changes to the MIP environment or result.

## Linux evidence

Execution copy: `/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln`.
Local return: `remote_results/probe_20260916T132317Z/`.

- `result.json`: bounded command record and successful return gate.
- `source_gate.log`: local-to-remote source SHA-256 equality.
- `source_sha256.json`: exact transferred local input list.
- `artifact_hashes.log`: remote evidence hashes, checked against local bytes.
- `checks/` and `runs/`: raw test and scripted-run artifacts.

The host preflight found no ROS 2, Docker or pixi installation in its checked
environment. Cortex needs a separate isolated Linux dependency setup. No live
Cortex tool adapter exists yet: the current gateway uses the compatible
function-schema shape, without importing Cortex or claiming runtime reuse.

## Limitations and next acceptance boundary

Fixture geometry, visible labels, task decomposition and execution feedback
are injected test data. `query_depth` is fixture point distance and memory is
an event record; neither is the paper's sensing/graph implementation. Tests
prove rejection and sequencing behavior under those injections only.

The original Habitat-first direction was subsequently superseded by Dr Sun's
selection of the existing Isaac Lab/PCT/SCAN/V12 stack. The next upper-layer
integration must demonstrate Pi/Cortex-compatible dispatch against the real
backend, calibrated sensing, grounding, paper-style memory and independent
evaluation. A model-driven pilot must freeze model/prompts/episode/budgets and
report runtime completion separately from navigation success.

An initial smoke failed because the scripted-provider recorder tried to clone
Pi's executable tool functions. It was fixed by recording only serializable
model messages and tool schemas at that boundary. The final local and Linux
checks above passed; the earlier failed attempt is not counted as a successful
run. Source snapshots remain unmodified and no physical plugin was activated.
