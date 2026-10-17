"""Verify the native snapshot and a clean reconstruction without touching its parent."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
from native_gate import sha

HERE = Path(__file__).resolve().parent
TASK = Path('/private/tmp/vla_stop_audit_20261012')


class SourceInventoryTests(unittest.TestCase):
    def test_exact_inventory_and_package_snapshot(self):
        origins = json.loads((HERE / 'native_sources.json').read_text())
        parent = json.loads((TASK / 'recovery_v176/source_identity.json').read_text())
        self.assertEqual(origins['parent_files'], parent['files'])
        actual = {'src/' + str(p.relative_to(TASK / 'recovery_v196/src')): sha(p)
                  for p in (TASK / 'recovery_v196/src').rglob('*') if p.is_file()}
        self.assertEqual(actual, origins['expected_files'])
        self.assertEqual(len(actual), 272)
        self.assertEqual(origins['changed_files'], sorted(
            name for name, digest in actual.items() if parent['files'].get(name) != digest))
        self.assertEqual(origins['deleted_files'], sorted(
            name for name in parent['files'] if name.startswith('src/') and name not in actual))
        self.assertGreaterEqual(len(origins['changed_files']), 37)
        self.assertEqual(len(origins['deleted_files']), 33)
        for package in (HERE / 'src').iterdir():
            if not package.is_dir():
                continue
            local = {str(p.relative_to(HERE)): sha(p) for p in package.rglob('*') if p.is_file()}
            expected = {n: h for n, h in actual.items() if n.startswith('src/' + package.name + '/')}
            self.assertEqual(local, expected, package.name)

    def test_clean_materialization_and_duplicate_refusal(self):
        with tempfile.TemporaryDirectory(prefix='v196_materialize_') as directory:
            root = Path(directory)
            (root / 'recovery_v176').symlink_to(TASK / 'recovery_v176', target_is_directory=True)
            command = [sys.executable, str(HERE / 'prepare_native.py'), '--task-root', str(root)]
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            identity = json.loads((root / 'recovery_v196/source_identity.json').read_text())
            actual = {'src/' + str(p.relative_to(root / 'recovery_v196/src')): sha(p)
                      for p in (root / 'recovery_v196/src').rglob('*') if p.is_file()}
            self.assertEqual(actual, identity['files'])
            self.assertTrue(os.access(root / 'recovery_v196/src/lite3_nav2_bridge/scripts/mission_bridge', os.X_OK))
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('FileExistsError', result.stderr)


if __name__ == '__main__':
    unittest.main()
