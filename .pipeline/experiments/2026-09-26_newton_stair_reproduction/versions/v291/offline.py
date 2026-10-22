"""Freeze qualified inputs, then reuse the unchanged strict53 result criteria."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import time
import xml.etree.ElementTree as ET

R = Path('/home/ubuntu/sun/vla_v291_20261022')
P = Path('/home/ubuntu/sun/vla_v289_20261020')
V = R/'source'
PV = P/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions'
OUT = R/'benchmark'
MANIFEST = V/'native_manifest.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
save = lambda p, x: p.write_text(json.dumps(x, indent=2)+'\n')


def verify():
    m = json.loads(MANIFEST.read_text())
    for rel, h in m['source_files'].items():
        assert sha(V/rel) == h, rel
    for rel, h in json.loads((V/'source_inventory.json').read_text()).items():
        assert sha(R/'native'/rel) == h, rel
    for rel, h in m['installed_files'].items():
        assert sha(R/'native'/rel) == h, rel
    for rel, h in m['evaluator_files'].items():
        assert sha(R/rel) == h, rel
    assert sha(P/'cohort/cases_manifest.json') == m['cohort_sha256']
    assert sha(V/'offline.py') == m['matrix_adapter_sha256']
    for case, h in m['fixtures'].items():
        folder = P/'cohort/cases'/case
        assert sha(folder/'fixture.json') == h
        for rel, expected in json.loads((folder/'fixture.json').read_text())['files'].items():
            assert sha(folder/rel) == expected, (case, rel)
    return m


def freeze():
    assert not MANIFEST.exists()
    assert json.loads((R/'evidence/attempt02/receipt.json').read_text())['stage']=='passed'
    assert json.loads((R/'evidence/evaluators01.json').read_text())['passed']
    assert all(x['window_passed'] for x in json.loads((R/'evidence/controller_replay01.json').read_text())['cases'].values())
    assert json.loads((R/'evidence/stance_replay01.json').read_text())['new_physics_steps']==0
    inventory=json.loads((R/'evidence/attempt02/source_inventory.json').read_text())
    save(V/'source_inventory.json', inventory)
    for rel,h in inventory.items():
        assert sha(R/'native'/rel)==h,rel
        if (V/rel).exists(): assert sha(V/rel)==h,rel
    tests = []
    for p in sorted((R/'native/build').glob('*/test_results/*/*.xml')):
        if p.name in ['cpplint.xunit.xml', 'uncrustify.xunit.xml', 'xmllint.xunit.xml']:
            continue
        x = ET.parse(p).getroot()
        assert not list(x.iter('failure')) and not list(x.iter('error')), str(p)
        tests.append(dict(path=str(p.relative_to(R)), tests=len(list(x.iter('testcase'))), sha256=sha(p)))
    assert len(tests) >= 30
    cohort = json.loads((P/'cohort/cases_manifest.json').read_text())
    original = json.loads((PV/'v289/native_manifest.json').read_text())
    files = {str(p.relative_to(V)): sha(p) for p in V.rglob('*') if p.is_file() and '__pycache__' not in p.parts and 'results' not in p.parts and p.suffix != '.md'}
    installed = {str(p.relative_to(R/'native')): sha(p) for p in (R/'native/install').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    evaluators = {str(p.relative_to(R)): sha(p) for p in (R/'evaluation/build').iterdir() if p.is_file() and p.name in
        ['native_probe', 'geometry_contract_probe', 'captured_tracking_probe']}
    assert len(evaluators) == 3
    save(MANIFEST, dict(version='v291', parent_native='v290', frozen=True, physics_steps=0,
        parent_native_sha256=sha(Path('/home/ubuntu/sun/vla_v290_20261021/source/native_manifest.json')), source_files=files,
        matrix_adapter_sha256=sha(Path(__file__)), independent_audit_sha256=sha(PV/'v289/independent_source_audit.py'),
        source_inventory_sha256=sha(V/'source_inventory.json'), installed_files=installed, evaluator_files=evaluators,
        fixtures=original['fixtures'], physical_cases=cohort['physical_cases'], cohort_sha256=sha(P/'cohort/cases_manifest.json'),
        tests=tests, hard_radius_m=.35, sensor_period_s=.1, deadline_s=.1,
        policy_sha256=original['policy_sha256'], native_root=str(R/'native'), cohort_root=str(P/'cohort'),
        claim='Native component qualification and captured-neighborhood/controller replay. Physical acceptance remains untested.'))
    verify()


def audit(case):
    folder = OUT/case
    if not (folder/'route_margins.csv').exists():
        return dict(case_id=case, exit_code=0, evaluated=False)
    base = Path('/data/sun/vla_mppi_20261009')
    image = subprocess.check_output(['docker', 'image', 'inspect', 'ubuntu:22.04', '--format', '{{.Id}}'], text=True).strip()
    command = ['docker', 'run', '--rm', '--pull=never', '--user', f'{os.getuid()}:{os.getgid()}', '--cpus=2', '--memory=6g',
        '-e', 'OPENBLAS_NUM_THREADS=1', '-e', 'OMP_NUM_THREADS=1', '-v', str(P/'geometry_data')+':'+str(base)+':ro',
        '-v', str(P/'repo')+':'+str(base/'repo')+':ro',
        '-v', '/home/ubuntu/sun/vla_v234_20261017:/home/ubuntu/sun/vla_v234_20261017:ro',
        '-v', str(folder)+':/audit:rw', '--entrypoint', '/home/ubuntu/sun/vla_v234_20261017/env/newton_worker/bin/python', image,
        str(base/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v289/independent_source_audit.py'), 'route', '/audit']
    with (folder/'independent_audit.log').open('x') as stream:
        code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
    return dict(case_id=case, exit_code=code, evaluated=True)


def matrix():
    source = (V/'run_matrix.py').read_text()
    source = source[:source.rindex("if __name__=='__main__':main()")]
    scope = dict(__file__=str(V/'run_matrix.py'), __name__='strict_v291_matrix')
    exec(compile(source, str(V/'run_matrix.py'), 'exec'), scope)
    scope.update(verify=verify, audit=audit)
    scope['main']()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['freeze', 'verify', 'matrix'])
    args = parser.parse_args()
    dict(freeze=freeze, verify=verify, matrix=matrix)[args.mode]()
