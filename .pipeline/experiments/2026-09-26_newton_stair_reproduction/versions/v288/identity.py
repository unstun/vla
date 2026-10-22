"""Verify the frozen v288 native/cohort and inherited physical execution chain."""
from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
ROOT=Path('/home/sun/vla_exec/local_cost_crash_v288')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def verify_sources():
    report=load(HERE.parent/'v248/identity.py','original_bridge_chain').verify_sources()
    native=load(HERE/'run_matrix.py','v288_frozen_native').verify()
    review=load(HERE/'execution_admission.py','v288_execution_admission').verify()
    gate=json.loads((ROOT/'benchmark/offline_gate.json').read_text())
    selection=json.loads((HERE/'selection.json').read_text())
    assert [c['case_id'] for c in selection['selected']]==native['physical_cases']
    assert sha(HERE/'selection.json')==sha(ROOT/'benchmark/selection.json')
    identity=json.loads((HERE/'source_identity.json').read_text())
    for rel,h in identity['files'].items():assert sha(HERE/rel)==h,rel
    if (HERE/'manifest.json').exists():
        frozen=json.loads((HERE/'manifest.json').read_text())
        for rel,h in frozen['source_files'].items():assert sha(HERE/rel)==h,rel
    binding=json.loads((HERE/'fixture_binding.json').read_text())
    assert binding['native_manifest_sha256']==sha(HERE/'native_manifest.json')
    geometry=BASE/'geometry_physical_v282'
    for rel,h in json.loads((HERE.parent/'v280/results/fixture_files.json').read_text()).items():assert sha(geometry/rel)==h,rel
    original=json.loads((HERE.parent/'v282/fixture_binding.json').read_text())
    for name,h in original['new_metadata'].items():assert sha(geometry/'fixtures/building'/name)==h,name
    report.update(native_source_version='v288',execution='v288',bridge_source_version='v248',
        native_manifest_sha256=sha(HERE/'native_manifest.json'),benchmark_manifest_sha256=native['cohort_sha256'],
        execution_source_identity=sha(HERE/'source_identity.json'),hard_collision_support_m=.35,sensor_period_s=.1,
        explicit_goal_heading=True,driver_source_sha256=sha(HERE.parent/'v257/long_route_driver.py'),
        navigation_active_before_goal_required=True,benchmark_acceptance_passed=gate['passed'],
        execution_review_sha256=sha(HERE/'execution_review.json'))
    return report
