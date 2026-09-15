import argparse
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from deploy.omnivla_lite3_receive_only import lite3_client
from deploy.omnivla_lite3_receive_only.tests.common import minimal_jpeg


class ClientTests(unittest.TestCase):
    def test_capture_failure_is_fail_closed(self):
        completed = subprocess.CompletedProcess(
            args=["v4l2-ctl"], returncode=1, stdout=b"", stderr=b"device busy"
        )
        with mock.patch("subprocess.run", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "device busy"):
                lite3_client.capture_one_jpeg("/dev/video0", 1.0)

    def test_rtsp_capture_uses_only_reviewed_loopback_endpoint(self):
        with self.assertRaisesRegex(RuntimeError, "reviewed loopback"):
            lite3_client.capture_one_rtsp_jpeg("rtsp://example.invalid/test", 1.0)

    def test_rtsp_capture_accepts_single_completed_frame_at_deadline(self):
        def capture_side_effect(command, **kwargs):
            output = Path(command[-1].split("=", 1)[1].replace("%05d", "00000"))
            output.write_bytes(minimal_jpeg())
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])

        with mock.patch("subprocess.run", side_effect=capture_side_effect):
            frame = lite3_client.capture_one_rtsp_jpeg(
                "rtsp://127.0.0.1:8554/test", 1.0
            )
        self.assertEqual(frame, minimal_jpeg())

    def test_run_once_records_error_without_network_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            token = root / "token"
            token.write_text("token", encoding="utf-8")
            output = root / "runs"
            args = argparse.Namespace(
                instruction="move forward",
                output_dir=output,
                device="/dev/video0",
                rtsp_url=None,
                capture_timeout=1.0,
                token_file=token,
                server_url="http://127.0.0.1:1",
                timeout=0.1,
            )
            with mock.patch.object(lite3_client, "capture_one_jpeg", return_value=minimal_jpeg()):
                with mock.patch.object(
                    lite3_client, "post_inference", side_effect=RuntimeError("network down")
                ) as post:
                    with self.assertRaisesRegex(RuntimeError, "network down"):
                        lite3_client.run_once(args)
            self.assertEqual(post.call_count, 1)
            runs = list(output.iterdir())
            self.assertEqual(len(runs), 1)
            self.assertTrue((runs[0] / "frame.jpg").is_file())
            self.assertTrue((runs[0] / "error.json").is_file())


if __name__ == "__main__":
    unittest.main()
