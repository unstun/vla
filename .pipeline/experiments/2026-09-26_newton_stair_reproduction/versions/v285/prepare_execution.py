"""Bind the fixed physical cohort after complete geometry and explicit execution review."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=Path('/home/sun/vla_exec/local_search_tracking_v285')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'manifest.json').exists()
native=json.loads((HERE/'native_manifest.json').read_text())
from execution_admission import verify
review=verify()
gate=json.loads((ROOT/'benchmark/offline_gate.json').read_text())
selection=json.loads((ROOT/'benchmark/selection.json').read_text())
assert [c['case_id'] for c in selection['selected']]==native['physical_cases']
for name,dest in [('selection.json',HERE/'selection.json'),('offline_gate.json',HERE/'results/offline_gate.json')]:
    dest.parent.mkdir(exist_ok=True);shutil.copy2(ROOT/'benchmark'/name,dest)
for c in selection['selected']:
    p=ROOT/'cohort/cases'/c['case_id']/'scenario.json';assert sha(p)==c['scenario_sha256']
    q=HERE/'scenarios'/(c['case_id']+'.json');q.parent.mkdir(exist_ok=True);shutil.copy2(p,q)
binding=dict(native_manifest_sha256=sha(HERE/'native_manifest.json'),
    geometry_parent_native='v280',geometry_fixture_binding_sha256=sha(HERE.parent/'v282/fixture_binding.json'),
    fixture_root='/data/sun/vla_mppi_20261009/geometry_physical_v282/fixtures',
    hard_radius_m=.35,sensor_period_s=.1,geometry_unchanged=True)
(HERE/'fixture_binding.json').write_text(json.dumps(binding,indent=2)+'\n')
names=['launch.py','native_graph.py','newton_episode.py','navigation_physical.launch.py','case_binding.py',
    'preflight.py','preflight_runner.py','resource_admission.py','resource_probe.py','verify_case.py','verify_profile.py',
    'identity.py','execution_admission.py','execution_review.json','results/user_resource_decision.json','prepare_execution.py','freeze_execution.py','fixture_binding.json','selection.json']
files={name:sha(HERE/name) for name in names}
files.update({'scenarios/'+c['case_id']+'.json':sha(HERE/'scenarios'/(c['case_id']+'.json')) for c in selection['selected']})
identity=dict(version='v285',native='v285',benchmark='v285',bridge='v248',files=files,
    native_manifest_sha256=sha(HERE/'native_manifest.json'),cohort_sha256=native['cohort_sha256'],
    offline_gate_sha256=sha(HERE/'results/offline_gate.json'),
    execution_review_sha256=sha(HERE/'execution_review.json'),benchmark_acceptance_passed=gate['passed'],
    explicit_heading_driver_sha256=sha(HERE.parent/'v257/long_route_driver.py'))
(HERE/'source_identity.json').write_text(json.dumps(identity,indent=2)+'\n')
print(json.dumps(dict(execution_identity_sha256=sha(HERE/'source_identity.json'),physical_cases=native['physical_cases'])))
