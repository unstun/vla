import assert from "node:assert/strict";
import { test } from "node:test";
import { runSmoke } from "../offline_smoke.mjs";
import { startFixture } from "../fixture_process.mjs";
import { createNavigationAgent } from "../runtime.mjs";
import { fixtureModel, scriptedProvider } from "../scripted_provider.mjs";

test("real Pi loop handles rejections, fresh evidence and accepted fixture stop", async () => {
  const result = await runSmoke();
  assert.equal(result.assertions_passed, true);
  assert.equal(result.actual_llm_calls, 0);
  assert.equal(result.rejected_calls, 3);
  assert.equal(result.gateway_events.filter((event) => event.tool === "navigate_to").length, 2);
});

test("model final text cannot create navigation success", async () => {
  const fixture = await startFixture();
  try {
    const provider = scriptedProvider(["I have successfully arrived. STOP."]);
    const runtime = await createNavigationAgent({ baseUrl: fixture.url, model: fixtureModel, streamFn: provider.streamFn });
    await runtime.agent.prompt("fixture");
    assert.equal(runtime.getState().terminal, false);
    assert.equal(runtime.getTerminalCause(), "model_ended_without_accepted_stop");
  } finally { await fixture.close(); }
});

test("Pi rejects an unregistered raw tool before backend dispatch", async () => {
  const fixture = await startFixture();
  try {
    const provider = scriptedProvider([[["update_parameter", { component: "controller", speed: 99 }]], "done"]);
    const runtime = await createNavigationAgent({ baseUrl: fixture.url, model: fixtureModel, streamFn: provider.streamFn });
    await runtime.agent.prompt("fixture");
    const trace = await fetch(`${fixture.url}/trace`).then((response) => response.json());
    assert.equal(trace.events.length, 0);
    assert.ok(runtime.events.some((event) => event.type === "tool_execution_end" && event.isError));
    assert.equal(runtime.getState().terminal, false);
  } finally { await fixture.close(); }
});

test("turn budget terminates without fabricating a stop result", async () => {
  const fixture = await startFixture();
  try {
    const provider = scriptedProvider([[["observe", {}]]]);
    const runtime = await createNavigationAgent({ baseUrl: fixture.url, model: fixtureModel,
      streamFn: provider.streamFn, maxTurns: 1 });
    await runtime.agent.prompt("fixture");
    assert.equal(provider.inputs.length, 1);
    assert.equal(runtime.getTerminalCause(), "turn_budget_exhausted");
    assert.equal(runtime.getState().terminal, false);
  } finally { await fixture.close(); }
});

test("provider failure stays distinct from a voluntary final response", async () => {
  const fixture = await startFixture();
  try {
    const provider = scriptedProvider([]);
    const runtime = await createNavigationAgent({ baseUrl: fixture.url, model: fixtureModel, streamFn: provider.streamFn });
    await runtime.agent.prompt("fixture");
    assert.equal(runtime.getTerminalCause(), "provider_or_runtime_error");
    assert.equal(runtime.getState().terminal, false);
  } finally { await fixture.close(); }
});
