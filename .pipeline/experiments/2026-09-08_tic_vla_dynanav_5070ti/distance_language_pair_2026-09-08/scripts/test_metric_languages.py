import json
from pathlib import Path
import tempfile
import unittest

from distance_probe import ALLOWED_INSTRUCTIONS
from protocol import parse_command, read_instruction_request


class MetricLanguageTests(unittest.TestCase):
    def test_both_languages_pass_verbatim(self):
        for instruction in ALLOWED_INSTRUCTIONS:
            self.assertEqual(parse_command(instruction)['instruction'],instruction)
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'request.json'
                request={'instruction':instruction,'instruction_mode':'verbatim','inference_seed':36}
                path.write_text(json.dumps(request,ensure_ascii=False))
                self.assertEqual(read_instruction_request(path),request)


if __name__=='__main__':
    unittest.main()
