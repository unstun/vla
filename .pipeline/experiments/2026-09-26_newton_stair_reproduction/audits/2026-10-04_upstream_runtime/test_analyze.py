"""Check actual observer parsing, sequential round boundaries and bad ordering."""
import unittest
from analyze import parse_upstream


class Log:
    def __init__(self,text):self.text=text
    def read_text(self):return self.text


class ParserTests(unittest.TestCase):
    def test_original_three_attempt_chain_is_one_round(self):
        text='search\nV71_UPSTREAM_ROUND sequence=1 sim=43.7 start_wall=475.0 wall_ms=788.0 attempts=3 success=0\nV71_UPSTREAM_ROUND sequence=2 sim=44.2 start_wall=475.8 wall_ms=1.2 attempts=1 success=1'
        starts,rows=parse_upstream(Log(text))
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['rebound_attempts'],3)
        self.assertAlmostEqual(rows[0]['wall_s'],.788)
        self.assertFalse(rows[0]['success']);self.assertTrue(rows[1]['success'])
        self.assertEqual(rows[1]['start_line'],3)
    def test_reject_reordered_duplicate_observer(self):
        text='V71_UPSTREAM_ROUND sequence=1 sim=43.7 start_wall=475.0 wall_ms=788.0 attempts=3 success=0\n'
        with self.assertRaises(AssertionError):parse_upstream(Log(text+text))


if __name__=='__main__':unittest.main()
