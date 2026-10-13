"""PyZMQ REQ/REP transfers unchanged applied-state JSON into Linux storage.

Reference: pyzmq26.4.0 howto/serialization; no pickle and no custom framing.
The original snapshot parser and reader remain authoritative. Source times are
preserved; receipt never replaces a measurement timestamp.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

BASE = Path(__file__).resolve().parents[2]
if sys.platform == "darwin":
    sys.path.insert(0, str(BASE / "runtime/zmq_macos"))
import zmq


class AppliedClient:
    def __init__(self, port=46203):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.setsockopt(zmq.SNDTIMEO, 100)
        self.socket.setsockopt(zmq.RCVTIMEO, 100)
        self.socket.connect(f"tcp://127.0.0.1:{port}")

    def publish(self, payload):
        raw = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode()
        digest = hashlib.sha256(raw).hexdigest()
        self.last_attempt = {"sha256": digest, "sequence": payload["state_epoch"]["state_sequence"],
                             "send_started_monotonic_ns": time.monotonic_ns(), "timeout_ms": 100}
        self.socket.send(raw)
        self.last_attempt["send_completed_monotonic_ns"] = time.monotonic_ns()
        reply = self.socket.recv_json()
        self.last_attempt["reply_received_monotonic_ns"] = time.monotonic_ns()
        if not reply.get("ok") or reply.get("sha256") != digest or reply.get("sequence") != payload["state_epoch"]["state_sequence"]:
            raise RuntimeError(f"Applied evidence not acknowledged: {reply}")
        return reply

    def close(self):
        self.socket.close()
        self.context.term()


def serve(out):
    sys.path.insert(0, str(BASE / "runtime_sources/backend_adapter"))
    from backend_adapter.applied_evidence import AppliedCommandSnapshot, AppliedEvidenceReader
    request = json.loads((out / "episode_request.json").read_text())
    external = out / "artifacts/external_episode"
    external.mkdir(parents=True, exist_ok=True)
    last_sequence = -1
    # Keep per-control-step I/O inside Linux tmpfs. The existing verified
    # exec/tar copyback returns this audit after the episode, before teardown.
    with zmq.Context() as context, context.socket(zmq.REP) as socket, (external / "applied_channel.jsonl").open("w") as log:
        socket.setsockopt(zmq.LINGER, 0)
        socket.bind("tcp://0.0.0.0:46203")
        while True:
            raw = socket.recv()
            received_ns = time.monotonic_ns()
            try:
                data = json.loads(raw)
                snapshot = AppliedCommandSnapshot.from_mapping(data)
                age = (time.monotonic_ns() - snapshot.wall_monotonic_ns) / 1e9
                if snapshot.run_id != out.name or snapshot.run_epoch_ns != request["run_epoch_ns"]:
                    raise ValueError("Applied state run identity mismatch")
                if not 0 <= age <= snapshot.max_reader_age_s or snapshot.state_sequence <= last_sequence:
                    raise ValueError("Applied state stale, future or reordered")
                temporary = external / "current_command.json.tmp"
                temporary.write_bytes(raw)
                temporary.replace(external / "current_command.json")
                last_sequence = snapshot.state_sequence
                checked = AppliedEvidenceReader(external / "current_command.json").read()
                reply = {"ok": True, "sequence": last_sequence, "sha256": hashlib.sha256(raw).hexdigest(),
                         "receive_age_s": age, "linux_receive_ns": time.monotonic_ns()}
                reply["original_reader_sequence"] = checked.state_sequence
                finish = external / "finish_request.json"
                if finish.exists():
                    reply["finish_request"] = json.loads(finish.read_text())
            except Exception as error:
                reply = {"ok": False, "error": str(error)}
            reply["server_received_monotonic_ns"] = received_ns
            reply["server_prepared_monotonic_ns"] = time.monotonic_ns()
            log.write(json.dumps(reply) + "\n")
            log.flush()
            socket.send_json(reply)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    serve(parser.parse_args().output)
