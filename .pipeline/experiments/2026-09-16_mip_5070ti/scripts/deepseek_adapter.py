"""Task-owned DeepSeek Harness extension to the pinned MIP episode driver."""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from driver import SessionOutcome


# Disable model-visible host tools and prompt injection from repository skills.
# The MCP bridge itself publishes observe/step only when HABITAT_BARE=1.
DISABLED = """tool-bash tool-pwsh tool-jobs tool-fs tool-fs-search
agent-instructions skill-filesystem tool-skill plan-mode
subagent-spawn-in-process subagent-fork-in-process tool-subagent-control
tool-subagent-list-agents tool-subagent tool-subagent-fork
workflow-worker-thread tool-workflow tool-todo tool-goal tool-ralph
tool-web web-search-deepseek web-fetch-http goal-round-driver
session-title-llm session-telemetry-otel code-runtime""".split()


def overlay(root, ctx, endpoint=None):
    rows = [{"id": name, "disabled": True} for name in DISABLED]
    rows.extend([
        {"id": "tools", "config": {"mode": "native"}},
        {"id": "agent-loop", "config": {"agents": [], "maxParallelToolCalls": 1}},
        {"id": "agent-default-model", "config": {
            "provider": "deepseek-official", "model": ctx.model}},
        {"id": "llm-deepseek", "config": {
            "apiKeyEnv": "DEEPSEEK_API_KEY", "reasoningEffort": "high",
            "maxTokens": 8192,
            **({"baseURL": endpoint} if endpoint else {})}},
        {"insert": [
            {"id": "mip-events", "name": str(root / "scripts/dsh_events.mjs")},
            {"id": "mip-mcp", "name": "@deepseek-ai/dsh-mcp-client", "config": {
                "serverName": "env", "transport": "stdio",
                "command": sys.executable, "args": [str(ctx.bridge_path)],
                "env": ctx.bridge_env(), "cwd": str(ctx.workdir),
                "toolCallTimeoutMs": 120000, "failOnStartupError": True}},
        ]},
    ])
    return rows


def result_texts(message):
    """Collect text inside the DSH tool-result block without serializing images."""
    out = []
    def visit(value):
        if isinstance(value, dict):
            if value.get("type") == "text":
                out.append(value["text"])
            else:
                for child in value.values():
                    if isinstance(child, (dict, list)):
                        visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(message)
    return out


def replay_events(path, sink):
    reason = None
    calls = 0
    usage = {}
    allowed = {"mcp__env__observe", "mcp__env__step"}
    for line in path.read_text().splitlines():
        event = json.loads(line)
        kind, data = event["type"], event["data"]
        if kind == "request/header":
            names = {t["name"] for t in data["header"].get("tools", [])}
            if names != allowed:
                raise RuntimeError(f"Unexpected model-visible tools: {sorted(names)}")
        elif kind == "step/start":
            calls += 1
        elif kind == "tool/call":
            if data["name"] not in allowed:
                raise RuntimeError(f"Unexpected tool: {data['name']}")
            sink.emit("tool_use", {"name": data["name"], "id": data["callId"],
                                   "input": json.loads(data["arguments"])})
        elif kind == "tool/result":
            sink.emit("tool_result", {"texts": result_texts(data["message"]),
                                      "error": data.get("error")})
        elif kind == "assistant/message":
            for block in data["message"]["content"]:
                if block.get("type") == "text":
                    sink.emit("assistant_text", {"text": block["text"]})
            for key, value in (data.get("usage") or {}).items():
                if isinstance(value, (int, float)):
                    usage[key] = usage.get(key, 0) + value
        elif kind == "turn/end":
            reason = data["reason"]
    return reason, calls, usage


class DeepSeekAdapter:
    name = "deepseek-harness"

    def __init__(self, root, endpoint=None):
        self.root = Path(root).resolve()
        self.endpoint = endpoint
        self.dsh = self.root / "tools/deepseek_harness/node_modules/.bin/dsh"
        self.inherent = {
            "extension": "nonstandard user-selected MIP bare / DeepSeek Harness",
            "auth": "DEEPSEEK_API_KEY supplied on execution host",
            "tools": ["mcp__env__observe", "mcp__env__step"],
            "turn_cap": "no DSH hard turn cap; original 500-step and 2400s limits",
            "max_output_tokens_per_request": 8192,
            "reasoning_effort": "high",
            "vision_context": "DSH provider-managed image retention",
            "event_capture": "pinned session/event API; replay after CLI exits",
        }

    def env(self):
        env = os.environ.copy()
        env["PATH"] = str(self.root / "tools/node-v24.21.0-linux-x64/bin") + os.pathsep + env["PATH"]
        env["DSH_HOME"] = str(self.root / "dsh_home")
        env["DSH_TELEMETRY_DISABLED"] = "1"
        env["DSH_TOOLS_MODE"] = "native"
        return env

    def prepare(self, spec):
        if not os.environ.get("DEEPSEEK_API_KEY"):
            raise RuntimeError("Set DEEPSEEK_API_KEY on the server before launching an episode")
        self.inherent["dsh_version"] = subprocess.run(
            [str(self.dsh), "--version"], env=self.env(), text=True,
            capture_output=True, check=True).stdout.strip()
        if self.inherent["dsh_version"] != "0.1.5-rc.1":
            raise RuntimeError("DSH version differs from the validated preparation")
        commit = subprocess.run(
            ["git", "-C", str(self.root / "source/AgentCanvas"), "rev-parse", "HEAD"],
            text=True, capture_output=True, check=True).stdout.strip()
        if commit != "b2b363af80a010ea9f73a0be9d49bc75555efdef":
            raise RuntimeError("MIP source commit differs from the selected paper branch")

    def describe(self, ctx):
        return {"options": {"profile": "headless", "bare": True,
                             "patch": overlay(self.root, ctx, self.endpoint)}}

    async def run(self, ctx, sink):
        if not ctx.bare or ctx.go2 or ctx.wp or ctx.hybrid or ctx.benchmark != "r2r":
            raise ValueError("This preparation supports only the simulated R2R bare cell")
        prefix = ctx.raw_dir / f"episode_{ctx.index}"
        patch = prefix.with_suffix(".patch.json")  # JSON is a YAML subset.
        patch.write_text(json.dumps(overlay(self.root, ctx, self.endpoint), indent=2))
        events = prefix.with_suffix(".dsh.jsonl")
        if events.exists():
            raise FileExistsError(f"Refusing to overwrite an existing session: {events}")
        env = self.env()
        env["MIP_DSH_EVENTS"] = str(events)
        prompt = ctx.briefing + "\n\n" + ctx.first_prompt
        prefix.with_suffix(".prompt.txt").write_text(prompt)
        argv = [str(self.dsh), "--profile", "headless", "--patch", str(patch), prompt]
        error = None
        with prefix.with_suffix(".stdout.log").open("w") as out, \
                prefix.with_suffix(".stderr.log").open("w") as err:
            proc = await asyncio.create_subprocess_exec(
                *argv, cwd=ctx.workdir, env=env, stdout=out, stderr=err,
                start_new_session=True)
            try:
                await asyncio.wait_for(proc.wait(), ctx.episode_timeout)
            except (asyncio.TimeoutError, asyncio.CancelledError) as exc:
                error = "episode_timeout_or_cancelled"
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(proc.pid, signal.SIGTERM)
                try:
                    await asyncio.wait_for(proc.wait(), 5)
                except asyncio.TimeoutError:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(proc.pid, signal.SIGKILL)
                    await proc.wait()
                if isinstance(exc, asyncio.CancelledError):
                    raise
        reason, turns, usage = (None, 0, {})
        if events.exists():
            reason, turns, usage = replay_events(events, sink)
        if proc.returncode != 0 or not reason or reason.get("kind") != "completed":
            error = error or f"dsh_exit={proc.returncode}; turn_end={reason}"
        sink.emit("exit", {"exit_code": proc.returncode, "turn_end": reason})
        return SessionOutcome(usage=usage, turns=turns, error=error,
                              extra={"dsh_exit_code": proc.returncode, "turn_end": reason})

    def finalize(self, run_dir):
        return {"extension": "MIP DeepSeek Harness; not a published-paper result"}
