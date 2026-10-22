"""Count recorded physics, including packed captures, rather than launch ledgers."""
from pathlib import Path
import hashlib,json,tempfile,unittest,zipfile
from run_physical import recorded_physics_steps,resume_action

class AttemptAccounting(unittest.TestCase):
    def test_missing_and_zero_step_results_are_not_physical_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.assertIsNone(recorded_physics_steps(root))
            (root/'result.json').write_text(json.dumps(dict(physics_steps=0)))
            self.assertEqual(recorded_physics_steps(root),0)
            (root/'result.json').write_text(json.dumps(dict(physics_steps=1234)))
            self.assertEqual(recorded_physics_steps(root),1234)

    def test_packed_result_is_verified_before_counting(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);data=b'{"physics_steps":1234}'
            with zipfile.ZipFile(root/'raw_capture.zip','w') as archive:archive.writestr('result.json',data)
            receipt=dict(members={'result.json':dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())})
            (root/'raw_capture_manifest.json').write_text(json.dumps(receipt))
            self.assertEqual(recorded_physics_steps(root),1234)
            receipt['members']['result.json']['sha256']='0'*64
            (root/'raw_capture_manifest.json').write_text(json.dumps(receipt))
            with self.assertRaises(AssertionError):recorded_physics_steps(root)

    def test_existing_or_partial_attempt_is_never_retried(self):
        self.assertEqual(resume_action(None,False,False),'start_unattempted')
        self.assertEqual(resume_action(dict(stage='execution_closed_pending_analysis'),True,True),'skip_closed')
        for row,ledger,task in [(None,True,True),(None,False,True),(dict(formal_attempt_started=True),False,False)]:
            with self.assertRaises(RuntimeError):resume_action(row,ledger,task)

if __name__=='__main__':unittest.main()
