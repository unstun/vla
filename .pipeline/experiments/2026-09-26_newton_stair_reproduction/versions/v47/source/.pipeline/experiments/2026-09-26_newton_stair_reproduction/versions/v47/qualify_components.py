"""Bind final component evidence to the exact v47 source and installation."""
from pathlib import Path
import hashlib
import json
import re

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
ROOT=BASE.parents[2]
NATIVE=BASE/'runtime/scan70_feasible_window_v47'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    result=json.loads((HERE/'tests/attempt07/result.json').read_text())
    assert result['exit_code']==0 and result['native_passed'] and result['cache_passed'] and result['window_passed'] and result['source_unchanged']
    assert all(r['geometry_exact_parent'] for r in result['plans'])
    expected=json.loads((NATIVE/'source_sha256.json').read_text())
    for attempt in (6,7):
        request=json.loads((HERE/f'tests/attempt{attempt:02d}/request.json').read_text())
        assert request['native_source_sha256']==expected
    for filename in ('source_sha256.json','install_sha256.json'):
        rows=json.loads((NATIVE/filename).read_text())
        assert all(sha(NATIVE/name)==digest for name,digest in rows.items())
    build=json.loads((NATIVE/'build_result.json').read_text())
    assert build['passed'] and build['source_unchanged']
    inherited=json.loads((HERE.parent/'v45/component_qualification.json').read_text())
    fixtures={}
    for state in ('v33_stand','v32_stand'):
        log=(HERE/f'tests/attempt07/{state}_window.log').read_text()
        fixtures[state]=dict(checks=len(re.findall(r'V47_WINDOW_CHECK .* PASS',log)),
            skipped=re.findall(r'V47_WINDOW_SKIPPED (.*)',log),
            shorter_native_consumption_checked='V47_WINDOW_CHECK get_local_target_consumes_hint_and_keeps_goal PASS' in log,
            log_sha256=sha(HERE/f'tests/attempt07/{state}_window.log'))
    qualification=dict(cache_geometry_and_contract_passed=True,window_contract_passed=True,
        cpu_graph_exact_continuous_trace=inherited['cpu_graph_exact_continuous_trace'],
        native_checks=result['native_checks'],cache_checks=result['cache_checks'],window_fixtures=fixtures,
        component_result_sha256=sha(HERE/'tests/attempt07/result.json'),
        core_result_sha256=sha(HERE/'tests/attempt06/result.json'),
        native_install_verified_files=len(json.loads((NATIVE/'install_sha256.json').read_text())),
        controller_configuration_hz=30,global_configuration_hz=1,
        full_stack_validated=False,full_scene_30hz_validated=False,
        geometry_scope='Exact cold v32/v33 safety geometry; v32 additionally has actual accepted shorter-window consumption. v33 has no safe shorter window in the bounded fixture set.',
        v45_representative_cases='Log-selected only; no paired executable replay of the live v45 cases.')
    (HERE/'component_qualification.json').write_text(json.dumps(qualification,indent=2)+'\n')
    print(json.dumps(qualification,indent=2))


if __name__=='__main__':
    main()
