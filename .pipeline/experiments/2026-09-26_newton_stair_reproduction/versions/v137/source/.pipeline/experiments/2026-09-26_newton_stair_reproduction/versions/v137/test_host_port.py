"""Host migration must preserve physics and reject mismatched execution receipts."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


class HostPortTests(unittest.TestCase):
    def test_physics_and_planner_parameters_unchanged(self):
        for name in ('newton_episode.py', 'corner_scenario.json',
                     'navigation_contract.json', 'realtime_pacer.py', 'applied_channel.py'):
            parent = (HERE.parent/'v125'/name).read_text().replace('v125', 'v137').replace('V125', 'V137')
            self.assertEqual(parent, (HERE/name).read_text(), name)
        # Only the pinned negative map supplement is added to planner parameters.
        parent=(HERE.parent/'v133/building_planner.yaml').read_text()
        candidate=(HERE/'building_planner.yaml').read_text()
        stripped=''.join(line for line in candidate.splitlines(keepends=True)
                         if 'grid_map.support_gap_' not in line)
        self.assertEqual(parent,stripped)
        receipt=json.loads((HERE/'support_coverage_input.json').read_text())
        self.assertIn('    grid_map.support_gap_path: '+receipt['file'],candidate)
        self.assertIn('    grid_map.support_gap_fnv64: "'+receipt['fnv64']+'"',candidate)

    def test_wrong_receipt_variant_and_image_rejected_before_start(self):
        spec = importlib.util.spec_from_file_location('tested_gate', HERE/'native_gate.py')
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = {'passed': True, 'platform': 'linux/amd64', 'variant': 'baseline', 'image_id': 'tested'}
            path = root/'build_receipt.json'
            path.write_text(json.dumps(receipt))
            quality = root/'quality.json'
            quality.write_text(json.dumps({'passed': True, 'runtime_receipts': {'candidate': sha(path)}}))
            with patch.object(gate, 'HERE', root), patch.dict(os.environ, {
                    'V137_VARIANT': 'candidate', 'V137_BUILD_EVIDENCE': tmp, 'V137_NATIVE_CONTAINER': 'owned'}):
                with self.assertRaisesRegex(ValueError, 'platform/variant'):
                    gate.verify(root, {'quality_sha256': sha(quality)})
                receipt['variant'] = 'candidate'
                path.write_text(json.dumps(receipt))
                quality.write_text(json.dumps({'passed': True, 'runtime_receipts': {'candidate': sha(path)}}))
                with patch.object(gate.subprocess, 'check_output', return_value='different\n'):
                    with self.assertRaisesRegex(ValueError, 'Image differs'):
                        gate.verify(root, {'quality_sha256': sha(quality)})
                path.write_text(path.read_text()+' ')
                with self.assertRaisesRegex(ValueError, 'Unqualified'):
                    gate.verify(root, {'quality_sha256': sha(quality)})


if __name__ == '__main__':
    unittest.main()
