"""Reject incomplete qualification before Docker or physics can start."""
from pathlib import Path
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import native_gate as gate


class NativeGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.receipt = dict(passed=True, platform='linux/arm64', variant='candidate',
                            native_version='v194', native_packages_available=14,
                            image_id='sha256:test', files={})
        self.path = self.root / 'build_receipt.json'
        self.path.write_text(json.dumps(self.receipt))
        self.quality = dict(passed=True, native_version='v194', execution_platform='linux/arm64',
            native_packages_available=14, rebuilt_packages=11, unique_controller_gtest_cases=22,
            controller_gtest_cases=20, native_terminal_regressions=True, generated_profile_cases=2,
            actual_graph_verified=True, full_navigation_accepted=False, host_tests=1,
            native_colcon_summary=dict(tests=45, errors=0, failures=0, skipped=0),
            runtime_receipts={'candidate': gate.sha(self.path)},
            native_graph_preflight_sha256='a'*64, overlay_loaded_sha256='b'*64,
            host_test_results_sha256='c'*64)

    def invoke(self, quality=None, image='sha256:test'):
        (self.root / 'quality.json').write_text(json.dumps(quality or self.quality))
        with patch.object(gate, 'HERE', self.root), patch.dict(os.environ, {
            'V194_VARIANT': 'candidate', 'V194_BUILD_EVIDENCE': str(self.root),
            'V194_NATIVE_CONTAINER': 'test'}), patch.object(gate.platform, 'system', return_value='Darwin'), \
            patch.object(gate.platform, 'machine', return_value='arm64'), \
            patch.object(gate.subprocess, 'check_output', return_value=image), \
            patch.object(gate.subprocess, 'run', return_value=SimpleNamespace(stdout='V194_NATIVE_IDENTITY_PASS')):
            return gate.verify(self.root, {'quality_sha256': gate.sha(self.root / 'quality.json')})

    def test_missing_package_count_rejects_before_docker(self):
        del self.quality['native_packages_available']
        with patch.object(gate.subprocess, 'check_output') as docker:
            with self.assertRaisesRegex(ValueError, 'native_packages_available'):
                gate.validate_quality(self.quality)
            docker.assert_not_called()

    def test_incomplete_graph_and_failed_tests_reject(self):
        for field, value in [('actual_graph_verified', False), ('native_terminal_regressions', False),
                             ('native_colcon_summary', dict(tests=45, errors=0, failures=1, skipped=0))]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                gate.validate_quality(dict(self.quality, **{field: value}))

    def test_qualified_arm64_receipt_accepts(self):
        self.assertTrue(self.invoke()['passed'])

    def test_receipt_mutation_rejects(self):
        self.path.write_text(json.dumps(dict(self.receipt, native_version='v188')))
        with self.assertRaisesRegex(ValueError, 'Unqualified source/install receipt'):
            self.invoke()

    def test_wrong_image_rejects(self):
        with self.assertRaisesRegex(ValueError, 'Image differs'):
            self.invoke(image='sha256:wrong')

    def test_amd64_receipt_rejects_even_with_matching_digest(self):
        self.path.write_text(json.dumps(dict(self.receipt, platform='linux/amd64')))
        self.quality['runtime_receipts']['candidate'] = gate.sha(self.path)
        with self.assertRaisesRegex(ValueError, 'Wrong execution platform'):
            self.invoke()


if __name__ == '__main__':
    unittest.main()
