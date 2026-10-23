"""Decision regression: preserve missing/censored measurements and failed gates."""
import copy,unittest
from summarize import summarize

def fixture():
 rows=[]
 counts={'v290':{'D07':1,'CD12':1,'S04':1,'A04':3},'v291':{'D07':2,'CD12':2,'S04':3,'A04':3}}
 for case in counts['v290']:
  for version in counts:
   for repeat in (1,2,3):
    episode=dict(max_displacement_cm=2.,pd_entry_censored=False,pd_delay_s=.3,fixed_stand_s=4.)
    success=repeat<=counts[version][case]
    rows.append(dict(case_id=case,variant=version,repeat=repeat,success=success,arrival_and_pd=success,scanner_deadline_failures=0,nav_complete_wall_s=(100. if version=='v290' else 110.) if success else None,stop=dict(first=episode,episodes=[episode],worst_episode_cm=2.,restart_count=0)))
 return dict(full_geometry=True,runs=rows)

class SummaryContract(unittest.TestCase):
 def test_original_gate_uses_all24_and_real_completion_time(self):
  r=summarize(fixture());self.assertEqual(r['totals'],{'v290':6,'v291':10});self.assertTrue(r['first_review_passed']);self.assertAlmostEqual(r['a04_slowdown_fraction'],.1)

 def test_missing_and_no_pd_first_episode_are_not_zero_or_complete(self):
  data=fixture();band=[r for r in data['runs'] if r['variant']=='v291' and r['case_id']=='D07']
  band[0]['stop']=dict(first=None,episodes=[],worst_episode_cm=None,restart_count=0)
  e=dict(max_displacement_cm=9.,pd_entry_censored=True,pd_delay_s=None,fixed_stand_s=None)
  band[1]['stop']=dict(first=e,episodes=[e,copy.deepcopy(band[2]['stop']['first'])],worst_episode_cm=9.,restart_count=1)
  r=summarize(data);g=r['case_groups']['D07']['v291'];self.assertEqual(g['first_stop_observed_n'],2);self.assertEqual(g['first_stop_censored_n'],1);self.assertEqual(g['first_pd_entry_observed_n'],1);self.assertEqual(g['first_stop_observed_median_cm'],5.5);self.assertEqual(g['first_completed_stop_median_cm'],2.)
  self.assertIsNone(next(x for x in r['paired'] if x['case_id']=='D07' and x['repeat']==2)['first_complete_drift_delta_cm'])

 def test_failed_a04_and_missing_time_cannot_pass(self):
  data=fixture()
  for r in data['runs']:
   if r['variant']=='v291' and r['case_id']=='A04':r['nav_complete_wall_s']=None
  target=next(r for r in data['runs'] if r['case_id']=='A04' and r['variant']=='v291');target['success']=False;target['scanner_deadline_failures']=1
  r=summarize(data);self.assertFalse(r['first_review_passed']);self.assertFalse(r['first_review_gate']['a04_three_successes']);self.assertFalse(r['first_review_gate']['a04_wall_slowdown_max15pct']);self.assertIsNone(r['a04_slowdown_fraction'])

if __name__=='__main__':unittest.main()
