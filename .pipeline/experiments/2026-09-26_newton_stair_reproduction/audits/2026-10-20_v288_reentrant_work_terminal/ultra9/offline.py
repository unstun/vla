"""New-host identity and full53 execution; frozen planning/audit logic is reused."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path('/home/ubuntu/sun/vla_v288_20261020')
VERSIONS = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions'
HERE = VERSIONS / 'v288'
COHORT = ROOT / 'cohort'
OUT = ROOT / 'benchmark'
PRIVATE_PYTHON = '/home/ubuntu/sun/vla_v234_20261017/env/newton_worker/bin/python'
IMAGE = 'sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343'
MANIFEST = ROOT / 'migration/native_manifest01.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')

def qualify():
    receipt = ROOT / 'evidence/current_geometry01.json'
    assert not receipt.exists()
    text = (ROOT / 'evidence/geometry_contract01.log').read_text()
    contract = json.loads(next(line[len('CONTRACT '):] for line in text.splitlines() if line.startswith('CONTRACT ')))
    assert contract['feedback_pass'] == contract['feedback_total'] == 12
    assert contract['local_wall_rejected'] == 0
    cases = json.loads((COHORT / 'cases_manifest.json').read_text())['cases']
    legal = [c for c in cases if c['expected'] == 'admit']
    assert len(legal) == 50
    query = COHORT / 'queries.txt'
    assert not query.exists() and not (COHORT / 'margins.csv').exists()
    with query.open('x') as stream:
        for c in legal:
            p = c['start']
            stream.write(' '.join(map(str, [c['case_id'], *p['ground'][:2], p['ground'][2] + .3, p['yaw']])) + '\n')
    with (ROOT / 'evidence/all_starts01.log').open('x') as stream:
        code = subprocess.run([sys.executable, str(ROOT / 'run_native.py'), 'spawn'], stdout=stream, stderr=subprocess.STDOUT).returncode
    assert code == 0, code
    rows = list(csv.DictReader((COHORT / 'margins.csv').open()))
    assert len(rows) == 50
    assert {r['id'] for r in rows} == {c['case_id'] for c in legal}
    assert all(int(r['support_verdict']) == 0 and min(float(r['edge_margin']), float(r['solid_margin'])) >= .10 for r in rows)
    save(receipt, dict(passed=True, contract=contract, legal_starts=50, all_50_support_free=True,
        minimum_extra_edge_margin=min(float(r['edge_margin']) for r in rows),
        minimum_extra_solid_margin=min(float(r['solid_margin']) for r in rows),
        queries_sha256=sha(query), margins_sha256=sha(COHORT / 'margins.csv'),
        physics_steps=0, navigation_source_changed=False))

def freeze():
    assert not MANIFEST.exists()
    assert json.loads((HERE / 'native_manifest.json').read_text())['version'] == 'v288'
    original = json.loads((HERE / 'native_manifest.json').read_text())
    for rel, digest in original['source_files'].items():
        assert sha(HERE / rel) == digest, rel
    inventory = json.loads((ROOT / 'native/source_inventory.json').read_text())
    assert sha(ROOT / 'native/source_inventory.json') == original['source_inventory_sha256']
    for rel, digest in inventory.items():
        assert sha(ROOT / 'native' / rel) == digest, rel
    for filename in ('current_geometry01.json', 'geometry01_closed.json', 'native_binding01.json', 'build09_closed.json'):
        assert json.loads((ROOT / 'evidence' / filename).read_text())['passed'], filename
    assert json.loads((ROOT / 'evidence/cohort01.json').read_text())['stage'] == 'passed'
    assert json.loads((ROOT / 'evidence/components10.json').read_text())['stage'] == 'passed'
    cohort = json.loads((COHORT / 'cases_manifest.json').read_text())
    assert sha(COHORT / 'cases_manifest.json') == original['cohort_sha256']
    files = {}
    def include(path):
        files[str(path.relative_to(ROOT))] = sha(path)
    for rel in inventory:
        include(ROOT / 'native' / rel)
    for directory in (ROOT / 'native/install', ROOT / 'native/fixtures', COHORT / 'cases'):
        for path in directory.rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                include(path)
    # Protect helper dependencies and the complete frozen version snapshots used
    # by both the native probe and the unchanged independent raw-source auditor.
    for path in VERSIONS.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix in ('.py', '.cpp', '.h', '.hpp', '.yaml', '.yml', '.json', '.sh', '.xml', '.txt', '.inc', '.gdb'):
            include(path)
    evaluator_names = ('native_probe', 'geometry_contract_probe', 'continuity_probe', 'spawn_margin', 'terrain_search_probe', 'repair_probe', 'field_probe', 'work_probe')
    for name in evaluator_names:
        include(ROOT / 'evaluation03/build' / name)
    tests = []
    for directory in (ROOT / 'native/build/lite3_nav2_plugins/test_results', ROOT / 'native/regressions'):
        for path in directory.rglob('*.xml'):
            r = ET.parse(path).getroot()
            assert int(r.get('failures', 0)) == int(r.get('errors', 0)) == 0
            tests.append(dict(path=str(path.relative_to(ROOT)), tests=int(r.get('tests', 0)), sha256=sha(path)))
            include(path)
    assert len(tests) == 20 and sum(t['tests'] for t in tests) == 178
    binding = json.loads((ROOT / 'evidence/native_binding01.json').read_text())
    assert all(v['sha256'] == v['original_sha256'] for v in binding['metadata'].values())
    for name in ('run_native.py', 'derived_run_native.py', 'migration/offline.py', 'migration/offline02.py', 'cohort/cases_manifest.json', 'cohort/start_admission.json', 'cohort/policy_golden.json'):
        include(ROOT / name)
    fixture_hashes = {}
    max_scan = 0
    for c in cohort['cases']:
        folder = COHORT / 'cases' / c['case_id']
        fixture = json.loads((folder / 'fixture.json').read_text())
        assert fixture['physics_steps'] == 0 and fixture['max_scan_s'] <= .1
        max_scan = max(max_scan, fixture['max_scan_s'])
        for rel, digest in fixture['files'].items():
            assert sha(folder / rel) == digest, (c['case_id'], rel)
        fixture_hashes[c['case_id']] = sha(folder / 'fixture.json')
    save(MANIFEST, dict(version='v288', frozen=True, migration_only=False, navigation_source_changed=True,
        original_native_manifest_sha256=sha(HERE / 'native_manifest.json'), files=files,
        source_files=329, tests=tests, fixture_hashes=fixture_hashes, max_nominal_scan_s=max_scan,
        physical_cases=cohort['physical_cases'], cohort_sha256=sha(COHORT / 'cases_manifest.json'),
        cpu_limit=2, image=IMAGE, hard_radius_m=.35, sensor_period_s=.1,
        host_identity=subprocess.check_output(['uname', '-a'], text=True).strip(),
        host_cpu=subprocess.check_output(['lscpu'], text=True), frozen_utc_s=time.time(),
        claim='New v288 native binaries on ultra9; all53 immutable v286 ultra9 zero-step captures reused byte-exact'))
    print(json.dumps(dict(frozen=True, files=len(files), manifest_sha256=sha(MANIFEST), max_scan_s=max_scan)), flush=True)

def verify():
    manifest = json.loads(MANIFEST.read_text())
    for rel, digest in manifest['files'].items():
        assert sha(ROOT / rel) == digest, rel
    assert subprocess.check_output(['docker', 'image', 'inspect', IMAGE, '--format', '{{.Id}}'], text=True).strip() == IMAGE
    return manifest

def audit(cid):
    folder = OUT / cid
    if not (folder / 'route_margins.csv').exists():
        return dict(case_id=cid, exit_code=0, evaluated=False)
    base = Path('/data/sun/vla_mppi_20261009')
    image = subprocess.check_output(['docker', 'image', 'inspect', 'ubuntu:22.04', '--format', '{{.Id}}'], text=True).strip()
    command = ['docker', 'run', '--rm', '--pull=never', '--user', f'{os.getuid()}:{os.getgid()}',
        '--cpus=2', '--memory=6g', '-e', 'OPENBLAS_NUM_THREADS=1', '-e', 'OMP_NUM_THREADS=1',
        '-v', str(ROOT / 'geometry_data') + ':' + str(base) + ':ro',
        '-v', str(ROOT / 'repo') + ':' + str(base / 'repo') + ':ro',
        '-v', '/home/ubuntu/sun/vla_v234_20261017:/home/ubuntu/sun/vla_v234_20261017:ro',
        '-v', str(folder) + ':/audit:rw', '--entrypoint', PRIVATE_PYTHON, image,
        str(base / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v288/independent_source_audit.py'), 'route', '/audit']
    with (folder / 'independent_audit.log').open('x') as stream:
        code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
    return dict(case_id=cid, exit_code=code, evaluated=True)

def matrix():
    verify()
    # Definitions and reporting stay exactly frozen. Only host identity, command
    # location and the canonical-path audit container differ from the old host.
    source = (HERE / 'run_matrix.py').read_text()
    source = source[:source.rindex("if __name__=='__main__':main()")]
    source = source.replace('max_workers=2', 'max_workers=4')
    old = "str(HERE/'run_native.py')"
    assert source.count(old) == 1
    source = source.replace(old, "str(ROOT/'run_native.py')")
    namespace = dict(__file__=str(HERE / 'run_matrix.py'), __name__='frozen_new_host_matrix')
    exec(compile(source, str(HERE / 'run_matrix.py'), 'exec'), namespace)
    namespace.update(ROOT=ROOT, OUT=OUT, COHORT=COHORT, PYTHON=PRIVATE_PYTHON, verify=verify, audit=audit)
    namespace['main']()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('qualify', 'freeze', 'verify', 'matrix'))
    args = parser.parse_args()
    dict(qualify=qualify, freeze=freeze, verify=verify, matrix=matrix)[args.mode]()
