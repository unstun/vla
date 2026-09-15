from http.client import HTTPConnection
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.parse import urlencode
import uuid

from deploy.omnivla_lite3_receive_only import protocol
from deploy.omnivla_lite3_receive_only.server import (
    FakeEngine,
    InferenceApplication,
    make_server,
)
from deploy.omnivla_lite3_receive_only.tests.common import minimal_jpeg, trajectory


class BlockingEngine:
    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()

    def infer(self, jpeg, instruction):
        del jpeg, instruction
        self.entered.set()
        self.release.wait(5)
        return trajectory()


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.token = "test-token-value"
        app = InferenceApplication(FakeEngine(), self.token, Path(self.temp.name))
        self.server = make_server("127.0.0.1", 0, app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.temp.cleanup()

    @property
    def address(self):
        return self.server.server_address

    def request(self, token=None, jpeg=None, instruction="move forward", request_id=None, **headers):
        if jpeg is None:
            jpeg = minimal_jpeg()
        if request_id is None:
            request_id = str(uuid.uuid4())
        digest = protocol.sha256_bytes(jpeg)
        standard = {
            "Authorization": "Bearer " + (self.token if token is None else token),
            "Content-Type": "image/jpeg",
            "Content-Length": str(len(jpeg)),
            "X-Request-ID": request_id,
            "X-Capture-UTC": protocol.utc_now(),
            "X-Image-SHA256": digest,
        }
        standard.update(headers)
        connection = HTTPConnection(*self.address, timeout=5)
        path = "/v1/infer?" + urlencode({"instruction": instruction})
        connection.request("POST", path, body=jpeg, headers=standard)
        response = connection.getresponse()
        body = response.read()
        connection.close()
        return response.status, json.loads(body), request_id

    def test_health_is_receive_only(self):
        connection = HTTPConnection(*self.address, timeout=5)
        connection.request("GET", "/v1/health")
        response = connection.getresponse()
        payload = json.loads(response.read())
        connection.close()
        self.assertEqual(response.status, 200)
        self.assertEqual(payload["bind_address"], "127.0.0.1")
        self.assertFalse(payload["actuation_enabled"])

    def test_valid_inference_round_trip(self):
        status, payload, request_id = self.request()
        self.assertEqual(status, 200)
        protocol.validate_success_response(payload, request_id)
        audit = Path(self.temp.name, "server_events.jsonl").read_text()
        self.assertIn("inference_succeeded", audit)
        self.assertNotIn(self.token, audit)

    def test_bad_token_is_rejected_before_engine(self):
        status, payload, _ = self.request(token="wrong")
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"], "unauthorized")
        self.assertFalse(payload["actuation_enabled"])

    def test_invalid_jpeg_and_digest_are_rejected(self):
        status, payload, _ = self.request(jpeg=b"not-a-jpeg")
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "invalid_request")
        status, payload, _ = self.request(**{"X-Image-SHA256": "0" * 64})
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "invalid_request")

    def test_oversize_is_rejected_without_body_read(self):
        request_id = str(uuid.uuid4())
        connection = HTTPConnection(*self.address, timeout=5)
        connection.putrequest("POST", "/v1/infer?instruction=move+forward")
        connection.putheader("Authorization", "Bearer " + self.token)
        connection.putheader("Content-Type", "image/jpeg")
        connection.putheader("Content-Length", str(protocol.MAX_JPEG_BYTES + 1))
        connection.putheader("X-Request-ID", request_id)
        connection.putheader("X-Capture-UTC", protocol.utc_now())
        connection.putheader("X-Image-SHA256", "0" * 64)
        connection.endheaders()
        response = connection.getresponse()
        payload = json.loads(response.read())
        connection.close()
        self.assertEqual(response.status, 413)
        self.assertEqual(payload["error"], "body_too_large")

    def test_busy_request_gets_conflict(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        blocker = BlockingEngine()
        app = InferenceApplication(blocker, self.token, Path(self.temp.name, "busy"))
        self.server = make_server("127.0.0.1", 0, app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

        result = []
        first = threading.Thread(target=lambda: result.append(self.request()), daemon=True)
        first.start()
        self.assertTrue(blocker.entered.wait(2))
        status, payload, _ = self.request()
        self.assertEqual(status, 409)
        self.assertEqual(payload["error"], "busy")
        blocker.release.set()
        first.join(2)
        self.assertEqual(result[0][0], 200)


if __name__ == "__main__":
    unittest.main()

