import { createAssistantMessageEventStream } from "@earendil-works/pi-ai";

export const fixtureModel = {
  id: "scripted-fixture", name: "Scripted fixture, no LLM inference", provider: "offline",
  api: "openai-completions", baseUrl: "http://127.0.0.1/unused", reasoning: false,
  input: ["text"], contextWindow: 32000, maxTokens: 1024,
  cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
};

export function scriptedProvider(turns) {
  let index = 0;
  const inputs = [];
  const streamFn = (model, context) => {
    if (index >= turns.length) throw new Error("script_exhausted");
    inputs.push(structuredClone({
      systemPrompt: context.systemPrompt, messages: context.messages,
      tools: context.tools?.map(({ name, description, parameters }) => ({ name, description, parameters })),
    }));
    const turn = turns[index++];
    const content = typeof turn === "string" ? [{ type: "text", text: turn }] :
      turn.map(([name, args], item) => ({ type: "toolCall", id: `call-${index}-${item}`, name, arguments: args }));
    const message = {
      role: "assistant", content, api: model.api, provider: model.provider, model: model.id,
      usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0,
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } },
      stopReason: typeof turn === "string" ? "stop" : "toolUse", timestamp: Date.now(),
    };
    const stream = createAssistantMessageEventStream();
    queueMicrotask(() => {
      stream.push({ type: "done", reason: message.stopReason, message });
      stream.end();
    });
    return stream;
  };
  return { streamFn, inputs };
}
