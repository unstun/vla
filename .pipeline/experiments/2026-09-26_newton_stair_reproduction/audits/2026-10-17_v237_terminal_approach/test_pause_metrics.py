import math
import unittest
from pause_metrics import low_speed_intervals, summarize

class PauseMetricsTest(unittest.TestCase):
    def test_v237_two_short_stops_count_without_counting_gap(self):
        rows=[dict(start_s=111.31045532226562,end_s=111.87014770507812),dict(start_s=112.86959838867188,end_s=113.52923583984375)]
        report=summarize(rows,109,114.5)
        self.assertEqual(report['count_ge_05s'],2);self.assertEqual(report['count_ge_1s'],0)
        self.assertAlmostEqual(report['cumulative_low_s'],1.219329833984375)
        c=report['split_clusters_ge_1s'][0]
        self.assertEqual(c['episodes'],2);self.assertGreater(c['span_s'],c['low_s'])
        self.assertAlmostEqual(c['span_s'],c['low_s']+sum(c['gaps_s']))

    def test_window_clipping_precedes_duration_thresholds(self):
        report=summarize([dict(start_s=10,end_s=12)],11.8,13)
        self.assertEqual(report['count_ge_05s'],0)
        self.assertAlmostEqual(report['cumulative_low_s'],.2)

    def test_gaps_nonfinite_and_moving_samples_break_stops(self):
        samples=[(0,1),(.02,0),(.04,0),(.2,0),(.22,math.nan),(.24,0),(.26,.05),(.28,0)]
        intervals=low_speed_intervals(samples)
        self.assertEqual(len(intervals),3)
        self.assertAlmostEqual(sum(p['duration_s'] for p in intervals),.08)

    def test_qualified_window_excludes_startup_and_terminal_hold(self):
        report=summarize(low_speed_intervals([(x*.02,0 if x<50 or x>100 else 1) for x in range(200)]),1,2)
        self.assertEqual(report['cumulative_low_s'],0)

    def test_invalid_native_clock_is_not_silently_joined(self):
        for rows in [[(0,0),(0,0)],[(1,0),(.9,0)],[(math.nan,0)]]:
            with self.assertRaises(ValueError):low_speed_intervals(rows)

if __name__=='__main__':unittest.main()
