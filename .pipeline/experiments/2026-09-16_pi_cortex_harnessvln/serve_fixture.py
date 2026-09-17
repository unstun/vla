"""Loopback-only fixture transport. No ROS, simulator, API key, or motion I/O."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from gateway import Gateway, TOOLS


def reject_nonfinite(value):
    raise ValueError(f"nonfinite_json_value: {value}")


def main():
    gateway = Gateway()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, value):
            payload = json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == "/catalog":
                self.reply(200, {"protocol": 1, "tools": TOOLS, "state": gateway.context()})
            elif self.path == "/trace":
                self.reply(200, {"events": gateway.events, "state": gateway.context(),
                                 "fixture_moves": gateway.world.moves})
            else:
                self.reply(404, {"error": "unknown_endpoint"})

        def do_POST(self):
            if self.path != "/call":
                self.reply(404, {"error": "unknown_endpoint"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384:
                    raise ValueError("invalid_content_length")
                payload = json.loads(self.rfile.read(length), parse_constant=reject_nonfinite)
                self.reply(200, gateway.dispatch(payload))
            except (ValueError, TypeError) as error:
                self.reply(400, {"ok": False, "error": str(error)})

    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        print(json.dumps({"url": f"http://127.0.0.1:{server.server_port}",
                          "evidence_kind": "deterministic_fixture"}), flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
