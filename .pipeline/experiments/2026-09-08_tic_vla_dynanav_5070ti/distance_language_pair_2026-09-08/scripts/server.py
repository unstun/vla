"""Mac-only UI and ASR server. Simulator traffic stays inside an SSH tunnel."""
import json
import http.client
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from protocol import parse_command
from speech import SpeechRecognizer

ROOT = Path(__file__).resolve().parents[1]
REMOTE = "/home/sun/vla_exec/2026-09-08_tic_vla_dynanav_5070ti"
PORT = 18765


def remote_request(path, payload=None, timeout=2):
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request("http://127.0.0.1:18766" + path, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def main():
    asr = SpeechRecognizer(ROOT)
    threading.Thread(target=asr.load, daemon=True).start()
    launch_lock = threading.Lock()
    launch_state = {"starting": False, "error": None, "time_unix": 0}
    events_lock = threading.Lock()

    def event(payload):
        with events_lock, (ROOT / "logs/ui_events.jsonl").open("a") as out:
            out.write(json.dumps(dict(payload, time_unix=time.time()), ensure_ascii=False) + "\n")

    def start_simulator():
        try:
            # Only literal, project-owned commands cross the shell boundary.
            remote_cmd = f"bash {REMOTE}/demo/scripts/launch_remote.sh"
            result = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12",
                                     "gpu5070ti", remote_cmd], capture_output=True, text=True, timeout=25)
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or "SSH launch failed")
        except Exception as error:
            launch_state.update(starting=False, error=str(error))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, status, data, mime="application/json; charset=utf-8"):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/favicon.ico":
                return self.respond(204, b"", "image/x-icon")
            if path in {"/", "/app.js", "/style.css"}:
                name = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}[path]
                mime = {"/": "text/html", "/app.js": "text/javascript", "/style.css": "text/css"}[path]
                return self.respond(200, (ROOT / "web" / name).read_bytes(), mime + "; charset=utf-8")
            if path == "/api/status":
                state = {"connected": False}
                try:
                    state.update(json.loads(remote_request("/status")))
                    state["connected"] = True
                    state["frame_age_seconds"] = max(0, state["server_time_unix"] - state.get("time_unix", 0))
                    state["stale"] = state["frame_age_seconds"] > 5
                    if state.get("ready"):
                        launch_state["starting"] = False
                except (OSError, ValueError, http.client.HTTPException):
                    pass
                if launch_state["starting"] and time.time() - launch_state["time_unix"] > 120:
                    launch_state.update(starting=False, error="启动超过两分钟，请检查启动日志后重试。")
                state.update(asr_status=asr.status, asr_error=asr.error, launch=launch_state.copy())
                return self.respond(200, state)
            if path in {"/api/third_person.jpg", "/api/front.jpg"}:
                try:
                    return self.respond(200, remote_request(path.removeprefix("/api")), "image/jpeg")
                except (OSError, http.client.HTTPException):
                    return self.respond(503, {"error": "实时画面暂不可用。"})
            self.respond(404, {"error": "Not found"})

        def do_POST(self):
            # No CORS; explicit custom header prevents cross-origin form submission.
            origin = self.headers.get("Origin")
            if self.headers.get("X-Demo-Request") != "1" or (origin and origin not in
                    {f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}):
                return self.respond(403, {"error": "Invalid request origin"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                limit = 4 * 1024 * 1024 if self.path == "/api/transcribe" else 4096
                if not 0 <= length <= limit:
                    raise ValueError("Request too large")
                body = self.rfile.read(length)
                if self.path == "/api/transcribe":
                    result = asr.transcribe(body)
                    event(dict(result, event="transcribed"))
                    return self.respond(200, result)
                if self.path == "/api/command":
                    payload = json.loads(body)
                    parsed = parse_command(payload.get("text"))
                    identity = str(uuid.uuid4())
                    result = json.loads(remote_request("/command", {"id": identity, "text": parsed["text"]}))
                    event(dict(result, event="submitted", source=payload.get("source", "text")))
                    return self.respond(200, result)
                if self.path == "/api/start":
                    with launch_lock:
                        if launch_state["starting"]:
                            return self.respond(200, {"starting": True})
                        try:
                            json.loads(remote_request("/status"))
                            return self.respond(200, {"already_running": True})
                        except (OSError, http.client.HTTPException):
                            pass
                        launch_state.update(starting=True, error=None, time_unix=time.time())
                        threading.Thread(target=start_simulator, daemon=True).start()
                    return self.respond(202, {"starting": True})
                self.respond(404, {"error": "Not found"})
            except urllib.error.HTTPError as error:
                self.respond(error.code, error.read())
            except (ValueError, TypeError, AttributeError) as error:
                self.respond(400, {"error": str(error)})
            except (OSError, http.client.HTTPException, subprocess.SubprocessError) as error:
                self.respond(503, {"error": "服务暂不可用：" + str(error)})

    print(f"DEMO_UI http://127.0.0.1:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
