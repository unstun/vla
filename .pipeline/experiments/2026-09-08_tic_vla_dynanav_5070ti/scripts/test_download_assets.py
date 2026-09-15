"""Regression for premature HTTP EOF and safe continuation of a partial file."""

import importlib.util
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

spec = importlib.util.spec_from_file_location("download_assets", Path(__file__).with_name("download_assets.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RangeResumeTest(unittest.TestCase):
    def test_truncation_and_ignored_range_never_corrupt_partial(self):
        payload = bytes(range(256)) * 8
        state = {"mode": "truncated"}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                start, end = map(int, self.headers["Range"].removeprefix("bytes=").split("-"))
                block = payload[start:end + 1]
                self.send_response(200 if state["mode"] == "ignored" else 206)
                self.send_header("Content-Range", f"bytes {start}-{end}/{len(payload)}")
                self.send_header("Content-Length", str(len(block)))
                self.send_header("Connection", "close")
                self.end_headers()
                truncate = state["mode"] == "truncated" or (state["mode"] == "parallel_fault" and start == 17)
                self.wfile.write(block[:13] if truncate else block)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                partial = Path(directory) / "asset.partial"
                partial.write_bytes(payload[:17])
                item = {"url": f"http://127.0.0.1:{server.server_port}/asset", "bytes": len(payload), "destination": "test"}
                with self.assertRaisesRegex(RuntimeError, "Truncated range"):
                    module.download_in_ranges(item, partial)
                self.assertEqual(partial.read_bytes(), payload[:17])
                state["mode"] = "ignored"
                with self.assertRaisesRegex(RuntimeError, "Unexpected range response"):
                    module.download_in_ranges(item, partial)
                self.assertEqual(partial.read_bytes(), payload[:17])
                state["mode"] = "complete"
                module.download_in_ranges(item, partial)
                self.assertEqual(partial.read_bytes(), payload)
                partial.write_bytes(payload[:17])
                with patch.object(module, "DOWNLOAD_CHUNK_BYTES", 256):
                    state["mode"] = "parallel_fault"
                    with self.assertRaisesRegex(RuntimeError, "1 ranges failed"):
                        module.download_in_ranges(item, partial, workers=4)
                    self.assertEqual(partial.read_bytes(), payload[:17])
                    self.assertEqual(len(list(partial.with_name(partial.name + ".chunks").glob("*.bin"))), 7)
                    state["mode"] = "complete"
                    module.download_in_ranges(item, partial, workers=4)
                self.assertEqual(partial.read_bytes(), payload)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
