"""Exercise evidence preservation and fail-closed resource admission."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import resume_post_reboot as resume


class ResumeGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.parent = self.root / 'parent'
        self.parent.mkdir()
        self.tags = [f'v147_full_candidate_attempt{n:02d}' for n in range(8, 14)]
        self.identities = {'boot_id': 'unchanged-boot', 'source': 'unchanged-source'}
        self.write('request.json', {'pid': 2147483647, 'tags': self.tags})
        rows = []
        for tag, terminal in zip(self.tags, ('FINISHED', 'FAILED')):
            path = self.root / 'results/recording_v147' / tag / 'outcome.json'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'terminal': terminal}))
            rows.append({'tag': tag, 'outcome_sha256': resume.original.sha(path)})
        self.progress = {'state': 'interrupted', 'active': None, 'completed': rows,
                         'error': "AssertionError('Other GPU compute tasks active; retain results and inspect')"}
        self.write('progress.json', self.progress)
        self.write('identities_before.json', self.identities)
        for target, field, value in [(resume, 'PARENT', self.parent),
                                     (resume, 'OUTPUT', self.root / 'continuation'),
                                     (resume, 'CONTROL', self.root / 'control'),
                                     (resume.original, 'TASK', self.root)]:
            guard = patch.object(target, field, value)
            guard.start()
            self.addCleanup(guard.stop)
        guard = patch.object(resume.post, 'identities', return_value=self.identities)
        self.mock_identity = guard.start()
        self.addCleanup(guard.stop)

    def write(self, name, value):
        (self.parent / name).write_text(json.dumps(value))

    def test_accepts_preserved_success_and_failure_prefix(self):
        self.assertEqual(len(resume.verify_parent()), 3)

    def test_refuses_changed_existing_outcome(self):
        path = self.root / 'results/recording_v147' / self.tags[1] / 'outcome.json'
        path.write_text('{"terminal":"FINISHED"}')
        with self.assertRaises(AssertionError):
            resume.verify_parent()

    def test_refuses_existing_remaining_attempt(self):
        (self.root / 'trials' / self.tags[2]).mkdir(parents=True)
        with self.assertRaises(AssertionError):
            resume.verify_parent()

    def test_refuses_dropped_failure(self):
        self.progress['completed'].pop()
        self.write('progress.json', self.progress)
        with self.assertRaises(AssertionError):
            resume.verify_parent()

    def test_refuses_changed_boot(self):
        self.mock_identity.return_value = {'boot_id': 'new-boot', 'source': 'unchanged-source'}
        with self.assertRaises(AssertionError):
            resume.verify_parent()

    def test_busy_host_never_launches_or_mutates_parent(self):
        before = resume.verify_parent()
        with patch.object(resume.post, 'resources', side_effect=AssertionError(
                'Post-reboot memory admission below20GiB')), \
                patch.object(resume.original, 'main') as launch, \
                patch('sys.argv', ['resume_post_reboot.py', '--wait-seconds', '0']):
            with self.assertRaisesRegex(RuntimeError, 'wait exhausted'):
                resume.main()
            launch.assert_not_called()
        self.assertFalse(resume.OUTPUT.exists())
        self.assertEqual(before, resume.verify_parent())
        self.assertEqual(json.loads((resume.CONTROL / 'state.json').read_text())['state'], 'interrupted')


if __name__ == '__main__':
    unittest.main()
