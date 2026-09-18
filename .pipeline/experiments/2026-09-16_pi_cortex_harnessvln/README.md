# Pi / Cortex HarnessVLN: Interface And Native Backend

Current status, 2026-09-16: the successful pilot described below is one bounded
result. Three later display probes failed SCAN resubmission, including display
off. A native replay isolated the endpoint-acceleration defect; its one-line
candidate passed 12/12 fixture calls and was adopted as `scan_04` on 2026-09-17
(`scan_fix_qualification/RESULT.md`, Isaac series 7/8). A PD stance hold for V12
stops followed (`stance_hold_qualification/RESULT.md`). NVIDIA RViz/NVENC display and
recording were verified separately. See the
[local archival handoff](../../handoffs/2026-09-16_harnessvln_local_archive.md)
for evidence and the next acceptance steps. The overall task remains in
progress; the archival draft awaits review.

Status: the offline Pi tool loop and a separate continuous Isaac/PCT/SCAN/V12
navigation service have passed their respective bounded checks. The real service
completed a mid-motion cancellation, confirmed stop, replanning to A and arrival
at B in one episode. See [P2B_RESULT.md](P2B_RESULT.md) for raw evidence and limits.
Connecting Pi/Cortex-compatible tools to that service, visual grounding, full
spatial graph memory, real SLAM and model-driven navigation remain open.

The same 16 tests also passed on the 5070 Ti Linux execution copy. See
[RESULT.md](RESULT.md) for the source/return hash proof and exact limitations.

The subsequent `navigation_service/` slice adds a separate persistent goal
lifecycle core. Lead acceptance passed 37 executor and 21 independent fault/
ordering tests locally and in actual Foxy Python 3.8.10 on 5070 Ti. It has an
explicit backend port and refuses execution by default. The later
`backend_adapter/`, `backend_ros/` and `isaac_runner/` packages bind it to native
PCT/SCAN and Isaac when explicitly configured. Pi/Cortex integration remains
separate. The first fixture result remains unchanged.
See the [lead acceptance](../../../.trellis/tasks/09-16-emos-harnessvln-reimplementation/research/acceptance/P2A_LEAD_REVIEW.md)
for source hashes, failed review rounds, port assumptions and remaining gates.

## Responsibility

- `pi/runtime.mjs`: actual Pi agent-core, one decision owner, sequential tools,
  one movement/stop operation per model response, fresh backend context and
  distinct budget/error/accepted-stop terminal reasons.
- `gateway.py`: typed tool catalog, active task/evidence state, call deduplication,
  target/observation checks and stop validation. `FixtureWorld` is a deterministic
  injected executor; it is not a robot or physics simulator.
- `serve_fixture.py`: loopback-only single-threaded JSON transport, no ROS or
  model credentials. It is a development endpoint, not a production action server.
- `pi/scripted_provider.mjs`: deterministic responses through Pi's stream API.
- `test_gateway.py`, `pi/test/runtime.test.mjs`: negative and integration cases.
- `verify.py`: bounded checks, raw logs and source hashes.
- `remote_probe.py`: whitelist source sync, pre-run hash gate, bounded Linux
  offline checks and verified artifact return to `remote_results/`.

The eight tool names follow the paper's roles. Their fixture semantics are
explicit: `query_depth` currently returns fixture point distance, panorama is
fixture metadata, and memory is a short event/visited-place record. These do
not implement RGB-D sensing, panoramic rendering or paper-equivalent ST Graph
retrieval. The two subgoals are a scripted test task, not an LLM task parser.
The 10-second freshness limit and 0.1-metre fixture arrival tolerance are local
test parameters, not claimed HarnessVLN constants.

## Run

From this directory:

```sh
npm --prefix pi ci --ignore-scripts --no-audit --no-fund
python3 verify.py
```

Node >=22.19.0 and Python 3 are required. Dependencies are local to `pi/` and
bound by `package-lock.json`; the real Pi version is 0.85.1. No model key or GPU
is used. The fixture server gets only PATH/PYTHONUNBUFFERED from the environment
and is stopped by the runner after each test. Check output is under `checks/`;
the full scripted Pi/model-input/tool trace is under `runs/offline_*/`.

The scripted case attempts an early stop, proposes two movements in one model
turn, queries stale geometry, then refreshes observations and completes two
fixture subgoals. Acceptance requires exactly two executor calls, all three
expected rejections, evidence-backed task transitions and accepted fixture stop.
Model prose claiming arrival and exhausted/error runs cannot count as a stop.

## Remaining integration

Dr Sun subsequently selected the existing machine-dog-nav Isaac Lab / Lite3
stack and eventual real deployment. The task design supersedes the earlier
Habitat-first proposal:

1. Connect Pi and the Cortex-compatible tool adapter to the now-tested native
   persistent goal/feedback/cancel service.
2. Replace fixture inputs with calibrated RGB-D and localization; implement
   paper-style task, reflection/event and graph memory, grounding and validation.
3. Expand the accepted flat-platform spatial pilot with fault/reconnect tests,
   then frozen language-driven Isaac cases.
4. Verify actual FAST-LIVO2/sensor replay and receive-only interfaces before
   separately authorized supervised physical trials.

The targeted 5070 Ti preflight confirmed the existing Isaac Lab conda
environment, native Building run/asset directories and Podman Foxy image
`e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8`.
The earlier Docker/default-PATH probe had missed those resources. Eight
existing bridge transport tests passed in that actual Foxy/rclpy/Python 3.8.10
image with read-only, hash-matched source and no GPU or network access. This
qualifies the tested bridge transport, not a simulator or navigation episode.
Evidence lives in the selected backend acquisition's
`validation/ros_transport_20260916T140123Z/`.

Local VLA code is the source of truth. Before any later remote run, sync only
this experiment and selected sources, prove matching source/config hashes, and
return raw events, observations, trajectory, metrics and hashes. MIP's frozen
configuration and prior result remain separate. No physical drivers are started.

See the [design](../../../.trellis/tasks/09-16-emos-harnessvln-reimplementation/design.md)
and [upstream record](../../../references/upstream/2026-09-16_pi_cortex_harnessvln/comparison.md).
