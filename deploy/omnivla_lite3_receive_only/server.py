"""Bounded receive-only HTTP service for OmniVLA trajectory inference."""

import argparse
import hmac
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

try:
    from . import protocol
except ImportError:  # Direct execution from the deployment directory.
    import protocol  # type: ignore


class FakeEngine:
    """Deterministic backend used only by protocol and deployment smoke tests."""

    def infer(self, jpeg: bytes, instruction: str) -> List[List[float]]:
        del jpeg, instruction
        return [[float(i), float(-i), 1.0, 0.0] for i in range(8)]


class InferenceApplication:
    def __init__(
        self,
        engine: Any,
        token: str,
        audit_dir: Path,
        source_commit: str = protocol.SOURCE_COMMIT,
        checkpoint_revision: str = protocol.CHECKPOINT_REVISION,
    ) -> None:
        if not token:
            raise ValueError("runtime token must not be empty")
        self.engine = engine
        self.token = token
        self.audit_dir = audit_dir
        self.source_commit = source_commit
        self.checkpoint_revision = checkpoint_revision
        self.inference_lock = threading.Lock()
        self.audit_lock = threading.Lock()
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(str(self.audit_dir), 0o700)

    def audit(self, event: Dict[str, Any]) -> None:
        record = dict(event)
        record.setdefault("utc", protocol.utc_now())
        line = protocol.canonical_json_bytes(record)
        path = self.audit_dir / "server_events.jsonl"
        with self.audit_lock:
            descriptor = os.open(
                str(path), os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600
            )
            try:
                os.write(descriptor, line)
            finally:
                os.close(descriptor)

    def health(self, bind_address: str, port: int) -> Dict[str, Any]:
        return {
            "schema_version": protocol.SCHEMA_VERSION,
            "status": "ready",
            "source_commit": self.source_commit,
            "checkpoint_revision": self.checkpoint_revision,
            "modality": protocol.MODALITY,
            "bind_address": bind_address,
            "port": port,
            "actuation_enabled": False,
        }


class ReceiveOnlyHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: Any,
        handler_class: Any,
        application: InferenceApplication,
    ) -> None:
        self.application = application
        super().__init__(server_address, handler_class)


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "OmniVLAReceiveOnly/1"
    protocol_version = "HTTP/1.1"

    @property
    def application(self) -> InferenceApplication:
        return self.server.application  # type: ignore[attr-defined,no-any-return]

    def log_message(self, format_string: str, *args: Any) -> None:
        self.application.audit(
            {
                "event": "http_access",
                "client": self.client_address[0],
                "message": format_string % args,
            }
        )

    def _json(self, status: int, payload: Dict[str, Any]) -> None:
        body = protocol.canonical_json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, code: str, message: str, request_id: str = "") -> None:
        self.application.audit(
            {
                "event": "request_rejected",
                "status": status,
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        )
        self._json(
            status,
            {
                "schema_version": protocol.SCHEMA_VERSION,
                "error": code,
                "message": message,
                "request_id": request_id,
                "actuation_enabled": False,
            },
        )

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/v1/health":
            self._error(HTTPStatus.NOT_FOUND, "not_found", "endpoint not found")
            return
        bind_address, port = self.server.server_address  # type: ignore[attr-defined]
        self._json(HTTPStatus.OK, self.application.health(bind_address, int(port)))

    def do_POST(self) -> None:
        self.connection.settimeout(protocol.REQUEST_IO_TIMEOUT_SECONDS)
        parsed = urlparse(self.path)
        if parsed.path != "/v1/infer":
            self._error(HTTPStatus.NOT_FOUND, "not_found", "endpoint not found")
            return

        request_id = self.headers.get("X-Request-ID", "")
        try:
            request_id = protocol.validate_request_id(request_id)
        except protocol.ProtocolError as exc:
            self._error(HTTPStatus.BAD_REQUEST, "invalid_request_id", str(exc))
            return

        authorization = self.headers.get("Authorization", "")
        expected = "Bearer " + self.application.token
        if not hmac.compare_digest(authorization, expected):
            self._error(HTTPStatus.UNAUTHORIZED, "unauthorized", "invalid bearer token", request_id)
            return
        if self.headers.get_content_type() != "image/jpeg":
            self._error(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "invalid_content_type",
                "Content-Type must be image/jpeg",
                request_id,
            )
            return
        try:
            content_length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._error(HTTPStatus.LENGTH_REQUIRED, "invalid_length", "Content-Length is required", request_id)
            return
        if content_length <= 0:
            self._error(HTTPStatus.BAD_REQUEST, "invalid_length", "JPEG body must not be empty", request_id)
            return
        if content_length > protocol.MAX_JPEG_BYTES:
            self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "body_too_large", "JPEG body exceeds limit", request_id)
            return

        queries = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=False)
        instructions = queries.get("instruction", [])
        if len(instructions) != 1:
            self._error(HTTPStatus.BAD_REQUEST, "invalid_instruction", "exactly one instruction is required", request_id)
            return
        try:
            instruction = protocol.validate_instruction(instructions[0])
            capture_utc = protocol.validate_capture_utc(
                self.headers.get("X-Capture-UTC", "")
            )
            expected_digest = protocol.validate_sha256(
                self.headers.get("X-Image-SHA256", ""), "image_sha256"
            )
        except protocol.ProtocolError as exc:
            self._error(HTTPStatus.BAD_REQUEST, "invalid_metadata", str(exc), request_id)
            return

        if not self.application.inference_lock.acquire(blocking=False):
            self._error(HTTPStatus.CONFLICT, "busy", "one inference is already running", request_id)
            return
        started = time.monotonic()
        try:
            body = self.rfile.read(content_length)
            if len(body) != content_length:
                raise protocol.ProtocolError("JPEG body ended before Content-Length")
            width, height, digest = protocol.validate_jpeg(body, expected_digest)
            trajectory = self.application.engine.infer(body, instruction)
            response = protocol.make_success_response(
                request_id=request_id,
                trajectory_normalized=trajectory,
                inference_ms=(time.monotonic() - started) * 1000.0,
                source_commit=self.application.source_commit,
                checkpoint_revision=self.application.checkpoint_revision,
            )
            self.application.audit(
                {
                    "event": "inference_succeeded",
                    "request_id": request_id,
                    "capture_utc": capture_utc,
                    "image_sha256": digest,
                    "image_width": width,
                    "image_height": height,
                    "instruction": instruction,
                    "inference_ms": response["inference_ms"],
                    "actuation_enabled": False,
                }
            )
            self._json(HTTPStatus.OK, response)
        except protocol.ProtocolError as exc:
            self._error(HTTPStatus.BAD_REQUEST, "invalid_request", str(exc), request_id)
        except Exception as exc:
            self._error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "inference_failed",
                "%s: %s" % (type(exc).__name__, exc),
                request_id,
            )
        finally:
            self.application.inference_lock.release()


def make_server(
    bind_address: str,
    port: int,
    application: InferenceApplication,
) -> ReceiveOnlyHTTPServer:
    return ReceiveOnlyHTTPServer((bind_address, port), RequestHandler, application)


def _load_token(path: Path) -> str:
    token = path.read_text(encoding="utf-8").strip()
    if not token:
        raise RuntimeError("runtime token file is empty")
    return token


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="192.168.2.109")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token-file", required=True, type=Path)
    parser.add_argument("--audit-dir", required=True, type=Path)
    parser.add_argument("--backend", choices=("fake", "original"), required=True)
    parser.add_argument("--upstream-root", type=Path)
    parser.add_argument("--checkpoint-path", type=Path)
    args = parser.parse_args()

    token = _load_token(args.token_file)
    if args.backend == "fake":
        engine: Any = FakeEngine()
    else:
        if args.upstream_root is None or args.checkpoint_path is None:
            parser.error("original backend requires --upstream-root and --checkpoint-path")
        try:
            from .engine_original import OriginalEngine
        except ImportError:
            from engine_original import OriginalEngine  # type: ignore
        engine = OriginalEngine(args.upstream_root, args.checkpoint_path)

    application = InferenceApplication(engine=engine, token=token, audit_dir=args.audit_dir)
    server = make_server(args.bind, args.port, application)
    application.audit(
        {
            "event": "server_started",
            "backend": args.backend,
            "bind_address": server.server_address[0],
            "port": server.server_address[1],
            "source_commit": application.source_commit,
            "checkpoint_revision": application.checkpoint_revision,
            "actuation_enabled": False,
        }
    )
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
        application.audit({"event": "server_stopped", "actuation_enabled": False})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
