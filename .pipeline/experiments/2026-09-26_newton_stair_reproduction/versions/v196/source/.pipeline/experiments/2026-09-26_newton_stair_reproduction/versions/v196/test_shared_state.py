"""Exercise closed shared-state identity and the actual Docker mount command."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from run_mac_full import container_command
import shared_state


class SharedStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / 'v196_test'
        self.external = self.out / 'artifacts/external_episode'
        self.external.mkdir(parents=True)
        self.values = {
            'current_command.json': {'run_id': self.out.name, 'run_epoch_ns': 42},
            'finish_request.json': {'run_id': self.out.name, 'observed_run_epoch_ns': 42,
                                    'backend_terminal_status': 'FINISHED'}}
        (self.out / 'episode_request.json').write_text(json.dumps(
            {'run_epoch_ns': 42, 'applied_transport': 'shared'}))
        for name, value in self.values.items():
            (self.external / name).write_text(json.dumps(value) + '\n')

    def docker_read(self, command, **kwargs):
        files = {}
        for name in shared_state.FILES:
            data = (self.external / name).read_bytes()
            files[name] = {'bytes': len(data), 'sha256': shared_state.hashlib.sha256(data).hexdigest()}
        return json.dumps(files)

    def test_shared_mount_has_no_shadow_or_applied_service(self):
        command = container_command(Path('/task'), self.out, self.out / 'evidence', 'test', 'image', 'run')
        self.assertIn(f'{self.out}:{self.out}:rw', command)
        self.assertNotIn('--tmpfs', command)
        self.assertFalse(any('24603' in item for item in command))

    def test_matching_closed_bytes_and_capture_accept(self):
        with patch.object(shared_state.subprocess, 'check_output', side_effect=self.docker_read):
            self.assertTrue(shared_state.verify_shared_state('test', self.out))
        class Capture:
            root = self.out
            def read(self, name): return (self.root / name).read_text()
            def json(self, name): return json.loads(self.read(name))
        self.assertTrue(shared_state.verify_capture(Capture()))
        (self.external / 'current_command.json').write_text('{}')
        with self.assertRaises(AssertionError):
            shared_state.verify_capture(Capture())

    def test_different_container_bytes_reject(self):
        with patch.object(shared_state.subprocess, 'check_output', return_value='{}'):
            self.assertFalse(shared_state.verify_shared_state('test', self.out))

    def test_foreign_epoch_rejects_before_docker(self):
        value = dict(self.values['current_command.json'], run_epoch_ns=43)
        (self.external / 'current_command.json').write_text(json.dumps(value))
        with patch.object(shared_state.subprocess, 'check_output') as docker:
            self.assertFalse(shared_state.verify_shared_state('test', self.out))
            docker.assert_not_called()

    def test_missing_finish_preserves_failure(self):
        (self.external / 'finish_request.json').unlink()
        self.assertFalse(shared_state.verify_shared_state('test', self.out))


if __name__ == '__main__':
    unittest.main()
