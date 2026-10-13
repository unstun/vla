"""Guard zero/turn separation, spline interpretation and immutable capture reads."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from analyze import groups, prepare_curve, boundary_distance, ZERO, FLOOR
from extract import verified_lines


class AnalysisTests(unittest.TestCase):
    def test_zero_and_turn_are_not_low_walking(self):
        commands=np.array([[0,0,0],[0,0,1],[.3,.4,0],[.6,0,0],[0,.59,0],[0,0,0]])
        norm=np.linalg.norm(commands[:,:2],axis=1)
        low=(norm>ZERO)&(norm<FLOOR)
        self.assertEqual(groups(low),[(2,3),(4,5)])
        self.assertEqual(groups(np.zeros(0,dtype=bool)),[])

    def test_native_cubic_linear_path_and_boundary_distance(self):
        # An exactly linear cubic Bezier curve x(t)=t, 0<=t<=1.
        d=dict(order=3,pos_pts=[dict(x=x,y=0,z=0) for x in (0,1/3,2/3,1)],
               knots=[0,0,0,0,1,1,1,1],start_time=dict(sec=0,nanosec=0))
        c=prepare_curve(d)
        np.testing.assert_allclose(c['speed'],1.,atol=1e-12)
        self.assertAlmostEqual(c['distance'][-1],1.)
        self.assertEqual(c['cruise_samples'],len(c['grid']))
        self.assertAlmostEqual(boundary_distance(0),.3975)

    def test_capture_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);raw=b'{"x":1}\n'
            (root/'sample.jsonl').write_bytes(raw)
            (root/'raw_capture_manifest.json').write_text(json.dumps(dict(members={
                'sample.jsonl':dict(bytes=len(raw),sha256='0'*64)})))
            with self.assertRaises(AssertionError):
                list(verified_lines(root,'sample.jsonl',{}))
            (root/'raw_capture_manifest.json').write_text(json.dumps(dict(members={
                'sample.jsonl':dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())})))
            sources={};self.assertEqual(list(verified_lines(root,'sample.jsonl',sources)),[(1,{'x':1})])
            self.assertTrue(sources['sample.jsonl']['archive_manifest_matched'])


if __name__=='__main__':unittest.main()
