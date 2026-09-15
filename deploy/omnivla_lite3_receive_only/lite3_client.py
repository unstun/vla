"""One-shot Lite3 camera client; it has no robot actuation capability."""

import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import uuid

try:
    from . import protocol
except ImportError:  # Direct execution from the deployment directory.
    import protocol  # type: ignore


def capture_one_jpeg(device: str, timeout_seconds: float) -> bytes:
    command = [
        "v4l2-ctl",
        "--device",
        device,
        "--stream-mmap",
        "--stream-count=1",
        "--stream-to=-",
    ]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        error = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError("v4l2 capture failed (rc=%d): %s" % (completed.returncode, error))
    return completed.stdout


def capture_one_rtsp_jpeg(rtsp_url: str, timeout_seconds: float) -> bytes:
    """Read one JPEG from the robot's existing loopback RTSP camera restream."""
    if rtsp_url != "rtsp://127.0.0.1:8554/test":
        raise RuntimeError("RTSP source is not the reviewed loopback camera endpoint")
    with tempfile.TemporaryDirectory(prefix="omnivla_rtsp_") as temporary:
        pattern = str(Path(temporary) / "frame-%05d.jpg")
        command = [
            "gst-launch-1.0",
            "-q",
            "rtspsrc",
            "location=" + rtsp_url,
            "protocols=tcp",
            "latency=100",
            "!",
            "rtph264depay",
            "!",
            "h264parse",
            "!",
            "avdec_h264",
            "!",
            "videoconvert",
            "!",
            "jpegenc",
            "!",
            "multifilesink",
            "max-files=1",
            "location=" + pattern,
        ]
        try:
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            completed = None
        frames = tuple(Path(temporary).glob("frame-*.jpg"))
        if len(frames) != 1:
            detail = "capture deadline expired" if completed is None else (
                completed.stderr.decode("utf-8", errors="replace").strip()
            )
            raise RuntimeError("RTSP capture failed: %s" % detail)
        return frames[0].read_bytes()


def post_inference(
    server_url: str,
    token: str,
    instruction: str,
    jpeg: bytes,
    request_id: str,
    capture_utc: str,
    timeout_seconds: float,
) -> Dict[str, Any]:
    instruction = protocol.validate_instruction(instruction)
    _, _, digest = protocol.validate_jpeg(jpeg)
    query = urlencode({"instruction": instruction})
    url = server_url.rstrip("/") + "/v1/infer?" + query
    request = Request(
        url=url,
        data=jpeg,
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "image/jpeg",
            "X-Request-ID": request_id,
            "X-Capture-UTC": capture_utc,
            "X-Image-SHA256": digest,
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        body = response.read(protocol.MAX_RESPONSE_BYTES + 1)
        if len(body) > protocol.MAX_RESPONSE_BYTES:
            raise protocol.ProtocolError("server response exceeds limit")
        if response.status != 200:
            raise RuntimeError("unexpected HTTP status %d" % response.status)
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise protocol.ProtocolError("server response is not valid UTF-8 JSON: %s" % exc)
    return protocol.validate_success_response(payload, request_id)


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(protocol.canonical_json_bytes(value))


def run_once(args: argparse.Namespace) -> Path:
    instruction = protocol.validate_instruction(args.instruction)
    request_id = str(uuid.uuid4())
    capture_utc = protocol.utc_now()
    run_dir = args.output_dir / (capture_utc.replace(":", "").replace("-", "") + "_" + request_id)
    run_dir.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    try:
        if args.rtsp_url:
            jpeg = capture_one_rtsp_jpeg(args.rtsp_url, args.capture_timeout)
            capture_source = args.rtsp_url
        else:
            jpeg = capture_one_jpeg(args.device, args.capture_timeout)
            capture_source = args.device
        width, height, digest = protocol.validate_jpeg(jpeg)
        frame_path = run_dir / "frame.jpg"
        frame_path.write_bytes(jpeg)
        _write_json(
            run_dir / "request.json",
            {
                "schema_version": protocol.SCHEMA_VERSION,
                "request_id": request_id,
                "capture_utc": capture_utc,
                "image_sha256": digest,
                "image_width": width,
                "image_height": height,
                "image_bytes": len(jpeg),
                "device": args.device,
                "capture_source": capture_source,
                "instruction": instruction,
                "server_url": args.server_url,
                "actuation_enabled": False,
            },
        )
        token = args.token_file.read_text(encoding="utf-8").strip()
        if not token:
            raise RuntimeError("runtime token file is empty")
        response = post_inference(
            server_url=args.server_url,
            token=token,
            instruction=instruction,
            jpeg=jpeg,
            request_id=request_id,
            capture_utc=capture_utc,
            timeout_seconds=args.timeout,
        )
        response["end_to_end_ms"] = (time.monotonic() - started) * 1000.0
        _write_json(run_dir / "response.json", response)
        (run_dir / "summary.txt").write_text(
            "request_id=%s\nimage_sha256=%s\ntrajectory_shape=8x4\n"
            "inference_ms=%.3f\nend_to_end_ms=%.3f\nactuation_enabled=false\n"
            % (
                request_id,
                digest,
                response["inference_ms"],
                response["end_to_end_ms"],
            ),
            encoding="utf-8",
        )
        return run_dir
    except Exception as exc:
        _write_json(
            run_dir / "error.json",
            {
                "schema_version": protocol.SCHEMA_VERSION,
                "request_id": request_id,
                "error_type": type(exc).__name__,
                "message": str(exc),
                "actuation_enabled": False,
            },
        )
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-url", default="http://192.168.2.109:8765")
    parser.add_argument("--instruction", required=True)
    parser.add_argument("--token-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--device", default="/dev/video0")
    parser.add_argument("--rtsp-url")
    parser.add_argument("--capture-timeout", type=float, default=10.0)
    parser.add_argument("--timeout", type=float, default=600.0)
    args = parser.parse_args()
    try:
        run_dir = run_once(args)
    except (HTTPError, URLError, OSError, RuntimeError, protocol.ProtocolError) as exc:
        print("receive-only request failed: %s: %s" % (type(exc).__name__, exc))
        return 1
    print("receive-only evidence: %s" % run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
