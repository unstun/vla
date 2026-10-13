import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from video_stream import VideoStream


class VideoTests(unittest.TestCase):
    def test_stream_keeps_three_samples_and_verified_video(self):
        with tempfile.TemporaryDirectory() as name:
            out=Path(name).resolve();stream=VideoStream(out,10,5)
            for i in range(5):stream.add(Image.new('RGB',(128,72),(i*40,40,80)),dict(physics_time_s=i/10))
            video=stream.close()
            self.assertTrue(video.is_file());self.assertFalse((out/'frames').exists())
            self.assertEqual(len(list((out/'frame_samples').iterdir())),3)
            self.assertEqual(json.loads((out/'video_verification.json').read_text())['frames'],5)
            rows=[json.loads(s) for s in (out/'frames.jsonl').read_text().splitlines()]
            self.assertEqual([r['physics_time_s'] for r in rows],[i/10 for i in range(5)])
            self.assertEqual(len({r['rgb24_sha256'] for r in rows}),5)

    def test_interruption_never_claims_complete(self):
        with tempfile.TemporaryDirectory() as name:
            out=Path(name).resolve();stream=VideoStream(out,10,5)
            stream.add(Image.new('RGB',(128,72)),{})
            stream.close(success=False)
            self.assertFalse((out/'newton_stair_recorded.mp4').exists())
            self.assertTrue((out/'video_interrupted.json').exists())

    def test_debug_frames_are_explicit(self):
        with tempfile.TemporaryDirectory() as name:
            out=Path(name).resolve();stream=VideoStream(out,10,2,keep_frames=True)
            for _ in range(2):stream.add(Image.new('RGB',(128,72)),{})
            stream.close();self.assertEqual(len(list((out/'frames').iterdir())),2)

    def test_changed_dimensions_fail(self):
        with tempfile.TemporaryDirectory() as name:
            out=Path(name).resolve();stream=VideoStream(out,10,2)
            stream.add(Image.new('RGB',(128,72)),{})
            with self.assertRaisesRegex(ValueError,'dimensions'):stream.add(Image.new('RGB',(64,48)),{})
            stream.close(success=False)


if __name__=='__main__':unittest.main()
