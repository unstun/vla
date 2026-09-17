"""Credential preflight must not log secrets or follow endpoint redirects."""
import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

import check_deepseek_access as probe


class AccessCheckTest(unittest.TestCase):
    def test_authentication_failure_is_single_attempt_and_redacted(self):
        secret = "test-private-sentinel"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "setup").mkdir()
            with patch.object(probe, "__file__", str(root / "scripts/probe.py")), \
                    patch.dict(probe.os.environ, {"DEEPSEEK_API_KEY": secret}, clear=True), \
                    patch.object(probe.urllib.request, "build_opener") as factory, \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                factory.return_value.open.side_effect = urllib.error.HTTPError(
                    "https://api.deepseek.com/models", 401, secret, None, None)
                self.assertEqual(probe.main(), 1)
                factory.return_value.open.assert_called_once()
            self.assertNotIn(secret, output.getvalue())
            report = json.loads(output.getvalue())
            self.assertEqual(report["error"], "authentication_rejected")
            self.assertEqual(report["http_status"], 401)

    def test_redirect_is_not_followed(self):
        paths = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                paths.append(self.path)
                self.send_response(302)
                self.send_header("Location", "/unexpected-recipient")
                self.end_headers()

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_port}/models",
                headers={"Authorization": "Bearer local-fixture-only"})
            opener = urllib.request.build_opener(probe.NoRedirect)
            with self.assertRaises(urllib.error.HTTPError) as error:
                opener.open(request, timeout=5)
            self.assertEqual(error.exception.code, 302)
            self.assertEqual(paths, ["/models"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
