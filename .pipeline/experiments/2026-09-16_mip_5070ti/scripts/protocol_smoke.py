"""Real DSH + original MCP + real Habitat, with a scripted local model endpoint.

This is an installation/interface smoke, not an LLM navigation experiment.
The fixture requests observe, left turn, observe, STOP, then finishes.
"""
import argparse
import asyncio
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import threading


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / "setup/protocol_smoke"
    output.mkdir(exist_ok=True)
    sys.path.insert(0, str(root / "source/AgentCanvas/coding-agent"))
    import cells
    from driver import run_cell
    from deepseek_adapter import DeepSeekAdapter
    requests_seen = []
    failures = []
    sequence = [
        ("mcp__env__observe", {}), ("mcp__env__step", {"actions": [2]}),
        ("mcp__env__observe", {}), ("mcp__env__step", {"actions": [0]}),
    ]

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if self.path != "/chat/completions":
                # Exercise the provider's documented inline-image fallback.
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'{"error":{"message":"fixture has no Files API"}}')
                return
            request = json.loads(body)
            names = sorted(t["function"]["name"] for t in request.get("tools", []))
            if names != ["mcp__env__observe", "mcp__env__step"]:
                failures.append({"unexpected_tools": names})
            n = len(requests_seen)
            images = sum(
                block.get("type") in ("image_url", "file")
                for msg in request.get("messages", [])
                for block in (msg.get("content") if isinstance(msg.get("content"), list) else [])
            )
            requests_seen.append({"request": n, "tools": names, "images": images,
                                  "model": request.get("model")})
            (output / "requests.json").write_text(json.dumps(requests_seen, indent=2))
            if n < len(sequence):
                name, arguments = sequence[n]
                delta = {"role": "assistant", "tool_calls": [{"index": 0,
                    "id": f"smoke_{n}", "type": "function", "function": {
                        "name": name, "arguments": json.dumps(arguments)}}]}
                finish = "tool_calls"
            else:
                delta = {"role": "assistant", "content": "Protocol smoke completed."}
                finish = "stop"
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for d, stop in [(delta, None), ({}, finish)]:
                chunk = {"id": f"smoke_{n}", "object": "chat.completion.chunk",
                         "created": 0, "model": "deepseek-flash", "choices": [
                             {"index": 0, "delta": d, "finish_reason": stop}]}
                self.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # Never contact the real provider or use user credentials in this fixture.
    os.environ["DEEPSEEK_API_KEY"] = "local-protocol-fixture-no-real-credential"
    cells.OUTPUT_ROOTS["deepseek"] = output
    cells.STD_FROZEN = {**cells.STD_FROZEN, "episode_timeout": 180}
    spec = cells.CellSpec(name="scripted_protocol_only", harness="deepseek",
                          model_key="deepseek-flash", model_id="deepseek-flash",
                          condition="bare", bare=True)
    run_name = spec.name + "_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    try:
        asyncio.run(run_cell(
            DeepSeekAdapter(root, f"http://127.0.0.1:{server.server_port}"), spec,
            ["http://127.0.0.1:19200"], episodes_spec="0", run_name=run_name))
    finally:
        server.shutdown()
        server.server_close()
    summary = json.loads((output / run_name / "summary.json").read_text())
    episodes = summary.get("episodes", [])
    if len(requests_seen) != 5 or not any(r["images"] for r in requests_seen):
        failures.append({"bad_request_sequence": requests_seen})
    if not episodes or any(e.get("error") for e in episodes):
        failures.append({"episode_errors": [e.get("error") for e in episodes]})
    if episodes and (episodes[0]["agent"]["tool_calls"] != {"observe": 2, "step": 2}
                     or episodes[0]["agent"]["env_steps"] != 2
                     or not episodes[0]["agent"]["called_stop"]):
        failures.append({"unexpected_actions": episodes[0]["agent"]})
    report = {"claim": "scripted local endpoint; not model navigation",
              "passed": not failures, "run_name": run_name,
              "requests": requests_seen, "failures": failures}
    (output / "result.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
