"""Pinned data pairing and unchanged navigation payload, independent of ROS."""
from pathlib import Path
import hashlib,importlib.util,sys,tempfile,unittest
import numpy as np
H=Path(__file__).resolve().parent;B=H.parents[1]
p=B/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_core.py'
spec=importlib.util.spec_from_file_location('surface_core',p);core=importlib.util.module_from_spec(spec);sys.modules[spec.name]=core;spec.loader.exec_module(core)
class SurfaceInputTests(unittest.TestCase):
    def setUp(self):
        self.map=core.load_pinned_map(B/'inputs/new_building.pickle')
        self.elev=core.load_paired_elevations(B/'inputs/new_building_original_precision.npz',self.map)
    def test_selected_and_surface_payloads(self):
        before=self.map['data'].tobytes()
        raw=core.load_surface_cost(B/'inputs/new_building_uninflated_cost.npz',self.map)
        surface=core.surface_evidence_points(self.map,self.elev,raw)
        nav=core.selected_ground_points(self.map,paired_elevations=self.elev)
        self.assertEqual(self.map['data'].tobytes(),before)
        self.assertEqual(hashlib.sha256(nav.astype('<f4').tobytes()).hexdigest(),'97d2dfbdb60c91e8473ab57f348923360f139da1130b4e9b7dd57e8655c15ca2')
        self.assertEqual(hashlib.sha256(surface.astype('<f4').tobytes()).hexdigest(),'f03b03c0b832bad2498c1823fd1c46e78ed3add1032f931571a202c208e430cf')
        self.assertEqual(len(surface),125493)
    def test_corrupt_surface_source_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            bad=Path(folder)/'cost.npz';bad.write_bytes(b'not the pinned array')
            with self.assertRaisesRegex(ValueError,'SHA-256'):core.load_surface_cost(bad,self.map)
    def test_map_mismatch_rejected(self):
        wrong=dict(self.map);wrong['data']=self.map['data'].copy();wrong['data'][3,0,0,0]=123
        with self.assertRaisesRegex(ValueError,'original PCT'):core.load_surface_cost(B/'inputs/new_building_uninflated_cost.npz',wrong)
if __name__=='__main__':unittest.main()
