"""Frozen matrix selection; exact requested positions/headings for every run."""
from pathlib import Path
import hashlib,json,os
HERE=Path(__file__).resolve().parent;CASE=os.environ['V263_CASE_ID']
selection=json.loads((HERE/'selection.json').read_text())
assert selection['physical_admission_passed'] and 8<=len(selection['selected'])<=10
record=next(r for r in selection['selected'] if r['case_id']==CASE)
SCENARIO=HERE/'scenarios'/(CASE+'.json')
def case_scenario(profile,wall_budget):
 assert profile=='generalization' and hashlib.sha256(SCENARIO.read_bytes()).hexdigest()==record['scenario_sha256']
 value=json.loads(SCENARIO.read_text());assert value['case_id']==CASE and 'goal_yaw_rad' in value
 value.update(max_sim_seconds=600.,max_wall_seconds=wall_budget,navigation_input='native PCT, original geometric LiDAR and measured simulator localization')
 return value
