"""A monitor restart must never become a second formal attempt."""
import unittest
from run_physical import resume_action


class ResumeContract(unittest.TestCase):
    def test_unstarted_case_can_start(self):
        self.assertEqual(resume_action(None, False, False), 'start_unattempted')

    def test_closed_attempt_is_skipped(self):
        self.assertEqual(resume_action(dict(stage='execution_closed_pending_analysis'),
                                       True, True), 'skip_closed')

    def test_interrupted_formal_attempt_needs_inspection(self):
        for row in (None, dict(stage='starting')):
            with self.assertRaises(RuntimeError):
                resume_action(row, True, True)

    def test_partial_preflight_is_not_overwritten(self):
        with self.assertRaises(RuntimeError):
            resume_action(dict(formal_attempt_started=False), False, True)

    def test_lost_ledger_cannot_allow_a_repeat(self):
        with self.assertRaises(RuntimeError):
            resume_action(dict(formal_attempt_started=True), False, False)


if __name__ == '__main__':
    unittest.main()
