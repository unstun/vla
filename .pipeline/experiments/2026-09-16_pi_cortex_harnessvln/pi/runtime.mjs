import { Agent } from "@earendil-works/pi-agent-core";

const allowed = new Set(["observe", "observe_panorama", "retrieve_memory", "ground_target",
  "query_depth", "navigate_to", "backtrack", "request_stop"]);
const operations = new Set(["navigate_to", "backtrack", "request_stop"]);

export async function createNavigationAgent({ baseUrl, model, streamFn, maxTurns = 32 }) {
  if (!Number.isInteger(maxTurns) || maxTurns < 1 || maxTurns > 128) throw new Error("invalid_turn_budget");
  const url = new URL(baseUrl);
  if (url.hostname !== "127.0.0.1" || url.protocol !== "http:") {
    throw new Error("offline_probe_requires_loopback_endpoint");
  }
  async function request(path, payload, signal) {
    const timeout = AbortSignal.timeout(5000);
    const response = await fetch(new URL(path, baseUrl), {
      method: payload ? "POST" : "GET",
      headers: { "Content-Type": "application/json" },
      body: payload ? JSON.stringify(payload) : undefined,
      signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
    });
    if (!response.ok) throw new Error(`gateway_http_${response.status}`);
    return response.json();
  }
  const catalog = await request("/catalog");
  if (catalog.protocol !== 1 || !Array.isArray(catalog.tools) || !catalog.state?.run_id) {
    throw new Error("invalid_gateway_catalog");
  }
  const names = catalog.tools.map((item) => item.function?.name);
  if (new Set(names).size !== names.length || names.some((name) => !allowed.has(name))) {
    throw new Error("unapproved_tool_catalog");
  }
  let state = catalog.state;
  let decision = 0;
  let operationUsed = false;
  const events = [];
  const agent = new Agent({
    initialState: {
      model,
      systemPrompt: "You are a navigation agent. Use only supplied tools and backend evidence. " +
        "After movement, refresh observations before grounding or stopping. " +
        "At most one movement or stop request per response. Text alone cannot complete a task.",
      tools: catalog.tools.map(({ function: spec }) => ({
        name: spec.name, label: spec.name, description: spec.description,
        parameters: spec.parameters, executionMode: "sequential",
        execute: async (callId, args, signal) => {
          const result = await request("/call", {
            run_id: state.run_id, call_id: callId, decision_id: decision,
            tool: spec.name, arguments: args,
          }, signal);
          if (typeof result.ok !== "boolean" || result.state?.run_id !== state.run_id) {
            throw new Error("invalid_gateway_result");
          }
          state = result.state;
          if (!result.ok) throw new Error(JSON.stringify({ code: result.error, status: result.status, state }));
          return { content: [{ type: "text", text: JSON.stringify(result) }], details: result };
        },
      })),
    },
    streamFn,
    toolExecution: "sequential",
    transformContext: async (messages) => [...messages, {
      role: "user", content: `Current backend evidence: ${JSON.stringify(state)}`, timestamp: Date.now(),
    }],
    beforeToolCall: async ({ toolCall }) => {
      if (state.terminal) return { block: true, reason: "episode_terminated" };
      if (operations.has(toolCall.name)) {
        if (operationUsed) return { block: true, reason: "one_operation_per_decision" };
        operationUsed = true;
      }
      return undefined;
    },
    shouldStopAfterTurn: () => state.terminal || decision >= maxTurns,
  });
  agent.subscribe((event) => {
    if (event.type === "turn_start") {
      decision += 1;
      operationUsed = false;
    }
    events.push(structuredClone(event));
  });
  return {
    agent, events,
    getState: () => structuredClone(state),
    getTerminalCause: () => state.terminal ? "accepted_fixture_stop" :
      agent.state.errorMessage ? "provider_or_runtime_error" :
      decision >= maxTurns ? "turn_budget_exhausted" : "model_ended_without_accepted_stop",
  };
}
