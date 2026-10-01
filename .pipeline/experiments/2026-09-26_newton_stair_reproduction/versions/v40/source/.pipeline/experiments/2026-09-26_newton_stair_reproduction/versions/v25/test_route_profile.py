from pathlib import Path
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

B=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('episode_profile',B/'scripts/run_local_episode.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class RouteProfileTests(unittest.TestCase):
    def test_existing_short_profile_unchanged(self):
        before=(B/'inputs/stair_scenario.json').read_bytes()
        expected=json.loads((B/'runs/v24_building_route01/inputs/stair_scenario.json').read_text())
        self.assertEqual(module.building_scenario('short_stair',600.),expected)
        self.assertEqual((B/'inputs/stair_scenario.json').read_bytes(),before)

    def test_historical_route_and_budget(self):
        scenario=module.building_scenario('historical_full',1500.)
        self.assertEqual(scenario['goal_ground_xyz_m'],[1.954685200623011,-2.9868112220934897,4.5330305099487305])
        self.assertEqual(scenario['spawn_ground_xyz_m'],[-5.545314788818359,6.01318883895874,.05804443359375])
        self.assertEqual(scenario['spawn_yaw_rad'],-1.3258179441604312)
        self.assertEqual(scenario['max_sim_seconds'],600.)
        self.assertEqual(scenario['max_wall_seconds'],1500.)

    def test_altered_profile_rejected(self):
        old=module.BASE
        try:
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder);(root/'inputs').mkdir()
                p=root/'inputs/historical_full_building.json'
                shutil.copyfile(B/'inputs/historical_full_building.json',p)
                d=json.loads(p.read_text());d['goal_ground_xyz_m'][2]=0.
                p.write_text(json.dumps(d))
                module.BASE=root
                with self.assertRaisesRegex(ValueError,'SHA-256'):
                    module.building_scenario('historical_full',1500.)
        finally:
            module.BASE=old

    def test_profile_requires_building_geometry(self):
        result=subprocess.run([sys.executable,str(B/'scripts/run_local_episode.py'),
            '--scene','flat_empty_long','--building-route','historical_full'],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertIn('requires scene building_full',result.stderr)

    def test_unknown_profile_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unknown'):
            module.building_scenario('automatic_guess',1500.)


if __name__=='__main__':
    unittest.main()
