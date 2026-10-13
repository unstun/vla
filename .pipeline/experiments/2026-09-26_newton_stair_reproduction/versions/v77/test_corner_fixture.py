"""Exercise the actual episode scenario seam and frozen profile refusal."""
from pathlib import Path
import json
import tempfile
import unittest

from corner_fixture import load_corner
from run_local_episode import building_scenario


class CornerTests(unittest.TestCase):
    def test_actual_episode_selects_corner_and_original_goal(self):
        fixture=load_corner();actual=building_scenario('corner_start',80.)
        for key in ('spawn_ground_xyz_m','spawn_yaw_rad','goal_ground_xyz_m','frame_id'):
            self.assertEqual(actual[key],fixture[key])
        self.assertEqual(actual['route_profile'],'corner_start')
        self.assertGreater(actual['spawn_ground_xyz_m'][2],3.)
        self.assertLess(abs(actual['spawn_ground_xyz_m'][0]-6.53891),1e-5)
    def test_reject_modified_source_profile(self):
        original=load_corner()
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'scenario.json'
            for field,value in [('spawn_ground_xyz_m',[0,0,0]),('goal_ground_xyz_m',[0,0,0]),('frame_id','robot')]:
                data=dict(original);data[field]=value;p.write_text(json.dumps(data))
                with self.assertRaises(ValueError):load_corner(p)


if __name__=='__main__':unittest.main()
