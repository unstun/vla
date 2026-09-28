"""Pair verification and unchanged selection around the measured precision bug."""
from pathlib import Path
import copy,hashlib,importlib.util,json,sys,tempfile,unittest
import numpy as np
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
spec=importlib.util.spec_from_file_location('precision_core',BASE/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_core.py');core=importlib.util.module_from_spec(spec);sys.modules[spec.name]=core;spec.loader.exec_module(core)
class PrecisionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.source=core.load_pinned_map(BASE/'inputs/new_building.pickle');cls.path=BASE/'inputs/new_building_original_precision.npz';cls.elevations=core.load_paired_elevations(cls.path,cls.source)
 def test_unchanged_xy_cost_selection_and_old_physical_contract(self):
  old=core.selected_ground_points(self.source);new=core.selected_ground_points(self.source,paired_elevations=self.elevations)
  self.assertEqual(new.shape,(86775,4));self.assertTrue(np.array_equal(old[:,[0,1,3]],new[:,[0,1,3]]))
  physical=core.selected_ground_points(self.source,cost_limit=None)
  self.assertEqual(hashlib.sha256(physical.astype('<f4').tobytes()).hexdigest(),'b357cd1317f06f73758e31d05613a55e204e4e5e05c17dcd5a4fcca140676313')
 def test_recorded_ground_endpoints_restore_original_band(self):
  old=core.selected_ground_points(self.source);new=core.selected_ground_points(self.source,paired_elevations=self.elevations);origin=old[:,:2].min(0)-.05
  mask=(np.floor((old[:,:2]-origin)/.1).astype(int)==[17,120]).all(1)
  records=json.loads((BASE/'audits/2026-09-27_v15_moving_frontier/blocking_raw_hits.json').read_text())['points'];rows=[r for r in records if r['cell']==[17,120]];self.assertEqual(len(rows),32)
  for r in rows:
   self.assertGreater(np.min(np.abs(old[mask,2].astype(float)-.03-r['xyz'][2])),.05)
   self.assertLessEqual(np.min(np.abs(new[mask,2].astype(float)-.03-r['xyz'][2])),.05)
 def test_corrupt_or_unpaired_source_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'bad.npz';path.write_bytes(b'wrong data')
   with self.assertRaises(ValueError):core.load_paired_elevations(path,self.source)
  source=copy.deepcopy(self.source);source['center'][0]+=.1
  with self.assertRaises(ValueError):core.load_paired_elevations(self.path,source)
  elevations=self.elevations.copy();elevations[0,26,133]+=.01
  with self.assertRaises(ValueError):core.selected_ground_points(self.source,paired_elevations=elevations)
if __name__=='__main__':unittest.main()
