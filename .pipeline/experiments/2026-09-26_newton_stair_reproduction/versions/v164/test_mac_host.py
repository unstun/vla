"""Host adaptation must preserve the original scene/physics/planner contracts."""
from pathlib import Path
import unittest

from mac_supervisor import verify_prepared_mount
from run_mac_full import container_command, validate_task
import tempfile

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / 'v149'


class MacHostTests(unittest.TestCase):
    def test_native_configuration_and_inputs_unchanged(self):
        for name in ['building_planner.yaml', 'navigation_contract.json',
                     'physical_floor_input.json', 'support_coverage_input.json',
                     'global_map_input.json', 'full_route_input.json', 'runtime_sync_manifest.json']:
            self.assertEqual((HERE / name).read_bytes(), (PARENT / name).read_bytes(), name)

    def test_physics_and_transport_code_only_renamed(self):
        for name in ['newton_episode.py', 'realtime_pacer.py', 'initial_frame_v142.py',
                     'body_tf_bridge.py', 'long_route_driver.py']:
            expected = (PARENT / name).read_text().replace('v149', 'v164').replace('V149', 'V164')
            self.assertEqual((HERE / name).read_text(), expected, name)

    def test_host_ports_and_readonly_source_mounts(self):
        task = Path('/private/tmp/vla_newton_v149_fixture')
        trial = task / 'v164_mac_full_attempt01'
        args = container_command(task, trial, trial / 'evidence', 'owned', 'sha256:test', trial.name)
        self.assertIn('--platform=linux/arm64', args)
        self.assertNotIn('--network=host', args)
        ports = [args[i + 1] for i, value in enumerate(args[:-1]) if value == '-p']
        self.assertEqual(ports, ['127.0.0.1:46202:46202', '127.0.0.1:46203:46203'])
        self.assertIn(f'{task}:/task:ro', args)
        self.assertIn('--memory=6g', args)

    def test_rejects_unowned_temp_root(self):
        with self.assertRaises(ValueError):
            validate_task(Path('/private/tmp/another_task'))

    def test_accepts_only_empty_prepared_mount(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'artifacts/external_episode').mkdir(parents=True)
            verify_prepared_mount(path)
            (path / 'artifacts/external_episode/evidence.json').write_text('{}')
            with self.assertRaises(FileExistsError):
                verify_prepared_mount(path)

    def test_mac_rss_unit_is_not_multiplied(self):
        self.assertNotIn('ru_maxrss', (HERE / 'mac_supervisor.py').read_text())
        self.assertIn('verify_prepared_mount', (HERE / 'mac_supervisor.py').read_text())


if __name__ == '__main__':
    unittest.main()
