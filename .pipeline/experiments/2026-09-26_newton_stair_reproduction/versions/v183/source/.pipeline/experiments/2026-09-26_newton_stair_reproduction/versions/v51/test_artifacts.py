import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
import artifacts as a


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.original=(a.BASE,a.AUDIT)
        a.BASE=Path(self.temp.name).resolve();a.AUDIT=a.BASE/"audit"
        self.run=a.BASE/"runs/render";self.run.mkdir(parents=True)
        self.source=a.BASE/"runs/source";self.source.mkdir()
        (self.source/"video_states.json").write_text('[{"physics_time_s":0}]')
        (self.run/"frames").mkdir()
        from PIL import Image
        rows=[]
        for i in range(4):
            p=self.run/"frames"/f"{i:06d}.png"
            Image.new("RGB",(64,48),(i*50,20,90)).save(p)
            rows.append({"file":str(p.relative_to(self.run)),"sha256":a.digest(p)})
        self.video=self.run/"test.mp4"
        subprocess.run([shutil.which('ffmpeg'),'-nostdin','-v','error','-framerate','10','-i',str(self.run/'frames/%06d.png'),'-c:v','libx264','-pix_fmt','yuv420p',str(self.video)],check=True)
        self.result=dict(video=str(self.video),video_sha256=a.digest(self.video),frames=4,fps=10,source_run='source',source_states_sha256=a.digest(self.source/'video_states.json'))
        (self.run/'result.json').write_text(json.dumps(self.result))
        (self.run/'frames.json').write_text(json.dumps(rows))

    def tearDown(self):
        a.BASE,a.AUDIT=self.original;self.temp.cleanup()

    def test_verified_prune_keeps_video_source_and_three_previews(self):
        proof=a.prune_frames(self.run,True)
        self.assertEqual(proof['status'],'completed')
        self.assertFalse((self.run/'frames').exists())
        self.assertEqual(len(list((self.run/'frame_samples').glob('*.png'))),3)
        self.assertEqual(a.digest(self.video),self.result['video_sha256'])
        self.assertTrue((self.source/'video_states.json').exists())

    def test_bad_video_identity_retains_every_frame(self):
        self.video.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'MP4 identity'):a.prune_frames(self.run,True)
        self.assertEqual(len(list((self.run/'frames').iterdir())),4)

    def test_count_mismatch_retains_every_frame(self):
        with self.assertRaisesRegex(ValueError,'frame count'):a.video_check(self.video,5,10)
        self.assertEqual(len(list((self.run/'frames').iterdir())),4)

    def test_bad_frame_retains_every_frame(self):
        (self.run/'frames/000001.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'PNG hash'):a.prune_frames(self.run,True)
        self.assertEqual(len(list((self.run/'frames').iterdir())),4)

    def test_active_run_refused(self):
        (self.run/'.artifact-active').write_text('running')
        with self.assertRaisesRegex(RuntimeError,'active'):a.prune_frames(self.run,True)

    def test_source_change_refused(self):
        (self.source/'video_states.json').write_text('[]')
        with self.assertRaisesRegex(ValueError,'recorded states'):a.prune_frames(self.run,True)

    def test_symlink_refused(self):
        p=self.run/'frames/000000.png';p.unlink();p.symlink_to(self.video)
        with self.assertRaisesRegex(ValueError,'non-symlink'):a.prune_frames(self.run,True)

    def test_transparent_log_compression_preserves_bytes_and_metadata(self):
        p=self.run/'closed.jsonl';p.write_bytes(b'{"repeated":"diagnostic data"}\n'*180000)
        old=p.stat();expected=a.digest(p)
        result=a.compress_log(p)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(a.digest(p),expected)
        self.assertEqual(p.stat().st_mtime_ns,old.st_mtime_ns)
        self.assertLess(p.stat().st_blocks,old.st_blocks)

    def raw_fixture(self):
        p=self.run/'clouds/00000.npz';p.parent.mkdir()
        import numpy as np
        np.savez_compressed(p,points=np.arange(24,dtype=np.float32).reshape(8,3))
        return p,a.digest(p)

    def test_archive_roundtrip_preserves_npz_and_text(self):
        p,expected=self.raw_fixture()
        log=self.run/'backend_states.jsonl';log.write_bytes(b'{"data":[]}\n'*500000)
        old_hash=a.digest(log)
        receipt=a.pack_raw(self.run)
        self.assertEqual(receipt['status'],'completed');self.assertFalse(p.exists())
        with a.open_text(self.run,'backend_states.jsonl') as stream:self.assertEqual(stream.readline(),'{"data":[]}\n')
        a.restore_raw(self.run)
        self.assertEqual(a.digest(p),expected);self.assertEqual(a.digest(log),old_hash)

    def test_archive_failed_verification_keeps_original(self):
        p,_=self.raw_fixture()
        with mock.patch.object(a,'archive_members',side_effect=ValueError('bad archive')):
            with self.assertRaisesRegex(ValueError,'bad archive'):a.pack_raw(self.run)
        self.assertTrue(p.exists())

    def test_corrupt_archive_refuses_restore(self):
        p,_=self.raw_fixture();a.pack_raw(self.run)
        with (self.run/'raw_capture.zip').open('ab') as stream:stream.write(b'changed')
        with self.assertRaisesRegex(ValueError,'Archive identity'):a.restore_raw(self.run)
        self.assertFalse(p.exists())

    def test_restore_does_not_overwrite_changed_file(self):
        p,_=self.raw_fixture();a.pack_raw(self.run);p.write_bytes(b'new user data')
        with self.assertRaisesRegex(ValueError,'overwrite changed'):a.restore_raw(self.run)
        self.assertEqual(p.read_bytes(),b'new user data')

    def test_failed_supervisor_without_result_can_archive(self):
        p,_=self.raw_fixture();(self.run/'result.json').unlink()
        (self.run/'process.json').write_text(json.dumps({'exit_code':7}))
        self.assertEqual(a.pack_raw(self.run)['status'],'completed')
        self.assertFalse(p.exists())

    def test_running_supervisor_without_result_refused(self):
        self.raw_fixture();(self.run/'result.json').unlink()
        (self.run/'process.json').write_text(json.dumps({'exit_code':None}))
        with self.assertRaisesRegex(RuntimeError,'completed process'):a.pack_raw(self.run)


if __name__=='__main__':unittest.main()
