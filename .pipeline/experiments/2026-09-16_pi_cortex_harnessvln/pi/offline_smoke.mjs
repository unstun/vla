import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { createNavigationAgent } from "./runtime.mjs";
import { startFixture } from "./fixture_process.mjs";
import { fixtureModel, scriptedProvider } from "./scripted_provider.mjs";

export async function runSmoke() {
  const fixture = await startFixture();
  const door = { target_id: "target-1", observation_id: "obs-1", subgoal_id: "sg-1" };
  const provider = scriptedProvider([
    [["observe", {}]],
    [["ground_target", { label: "doorway", observation_id: "obs-1", subgoal_id: "sg-1" }]],
    [["request_stop", { observation_id: "obs-1" }]],
    [["navigate_to", door], ["navigate_to", door]],
    [["query_depth", { target_id: "target-1", observation_id: "obs-1" }]],
    [["observe", {}]],
    [["ground_target", { label: "table", observation_id: "obs-2", subgoal_id: "sg-2" }]],
    [["navigate_to", { target_id: "target-2", observation_id: "obs-2", subgoal_id: "sg-2" }]],
    [["observe", {}]],
    [["request_stop", { observation_id: "obs-3" }]],
  ]);
  try {
    const runtime = await createNavigationAgent({ baseUrl: fixture.url, model: fixtureModel, streamFn: provider.streamFn });
    await runtime.agent.prompt("Pass through the doorway, then stop by the table. Offline contract fixture only.");
    const trace = await fetch(`${fixture.url}/trace`).then((response) => response.json());
    const errors = runtime.events.filter((event) => event.type === "tool_execution_end" && event.isError);
    assert.equal(runtime.getState().terminal, true);
    assert.equal(provider.inputs.length, 10);
    assert.equal(trace.fixture_moves, 2);
    for (const code of ["incomplete_task", "one_operation_per_decision", "stale_or_unknown_observation"]) {
      assert.ok(JSON.stringify(errors).includes(code), `Missing rejection: ${code}`);
    }
    assert.ok(JSON.stringify(provider.inputs[5]).includes("stale_or_unknown_observation"), "Error missing from next decision");
    assert.deepEqual(runtime.getState().subgoals.map((subgoal) => subgoal.evidence), ["obs-2", "obs-3"]);
    return {
      evidence_kind: "offline_protocol_probe", pi_runtime: "@earendil-works/pi-agent-core@0.85.1",
      actual_llm_calls: 0, cortex_runtime_executed: false, habitat_executed: false,
      fixture_moves: trace.fixture_moves, scripted_model_turns: provider.inputs.length,
      rejected_calls: errors.length, terminal_cause: runtime.getTerminalCause(),
      assertions_passed: true, state: runtime.getState(),
      pi_events: runtime.events, model_inputs: provider.inputs, gateway_events: trace.events,
    };
  } finally {
    await fixture.close();
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const result = await runSmoke();
  const directory = new URL(`../runs/offline_${new Date().toISOString().replace(/[:.]/g, "-")}/`, import.meta.url);
  await mkdir(directory, { recursive: true });
  await writeFile(new URL("trace.json", directory), JSON.stringify(result, null, 2) + "\n");
  const { pi_events, model_inputs, gateway_events, ...summary } = result;
  await writeFile(new URL("result.json", directory), JSON.stringify(summary, null, 2) + "\n");
  console.log(JSON.stringify({ ...summary, artifacts: directory.pathname }, null, 2));
}
