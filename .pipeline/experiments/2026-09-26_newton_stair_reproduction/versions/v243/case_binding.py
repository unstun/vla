"""Frozen case selection and exact scenario contract, shared by launch tools."""
from pathlib import Path
import hashlib,json,os

HERE=Path(__file__).resolve().parent
CASE=os.environ['V243_CASE_ID']
selection=json.loads((HERE/'selection.json').read_text())
if not selection.get('physical_admission_passed',False):
    raise RuntimeError('v243 physical launch blocked: the frozen matrix has fewer than two eligible cases')
record=next(r for r in selection['selected'] if r['case_id']==CASE)
SCENARIO=HERE/'scenarios'/(CASE+'.json')

def case_scenario(profile,wall_budget):
    assert profile=='generalization'
    assert hashlib.sha256(SCENARIO.read_bytes()).hexdigest()==record['scenario_sha256']
    value=json.loads(SCENARIO.read_text())
    assert value['case_id']==CASE and value['route_profile']==profile
    value.update(max_sim_seconds=600.,max_wall_seconds=wall_budget,
        navigation_input='native PCT map, actual geometric LiDAR and simulator body localization')
    return value
