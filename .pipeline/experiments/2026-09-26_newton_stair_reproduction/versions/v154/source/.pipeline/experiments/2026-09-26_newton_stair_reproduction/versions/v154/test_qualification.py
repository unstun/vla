"""The real launcher requires both pinned native evidence and package count."""
import json,unittest
from pathlib import Path
class Qualification(unittest.TestCase):
 def test_actual_launcher_metadata(self):
  here=Path(__file__).resolve().parent
  old=json.loads((here.parent/'v153/quality.json').read_text());new=json.loads((here/'quality.json').read_text())
  self.assertIsNone(old.get('native_packages_available',old.get('native_packages_built')))
  self.assertTrue(new['passed']);self.assertEqual(new['native_packages_available'],14);self.assertEqual(new['native_component_tests'],38)
  self.assertIn('candidate',new['runtime_receipts'])
if __name__=='__main__':unittest.main()
