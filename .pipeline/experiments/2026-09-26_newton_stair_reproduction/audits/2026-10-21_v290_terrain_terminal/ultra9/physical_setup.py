"""Prepare a private execution package without changing frozen navigation."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import time

R=Path('/home/ubuntu/sun/vla_v290_20261021')
P=Path('/home/ubuntu/sun/vla_v289_20261020')
M=R/'migration'
VERSIONS=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def prepare():
    receipt=R/'evidence/physical_setup01.json'
    assert not receipt.exists()
    ledger=json.loads((R/'benchmark/native_ledger.json').read_text())
    assert len(ledger)==53 and all(x['state']=='finished' for x in ledger)
    assert not (M/'physical_manifest01.json').exists()
    if not (R/'repo').exists():shutil.copytree(P/'repo',R/'repo')
    version=VERSIONS/'v290'
    shutil.copytree(M/'runtime_version',version,dirs_exist_ok=True)
    shutil.copy2(M/'physical_template.py',version/'launch.py')
    for name in ['native_manifest.json','source_inventory.json','src']:
        link=version/name
        if not link.exists():link.symlink_to(R/'source'/name,target_is_directory=name=='src')
        else:assert link.is_symlink() and link.resolve()==(R/'source'/name).resolve()
    for name in ['cohort','geometry_data','environment_score_v224']:
        link=R/name
        if not link.exists():link.symlink_to(P/name,target_is_directory=True)
        else:assert link.is_symlink() and link.resolve()==(P/name).resolve()
    fixture=R/'native/fixtures'
    if fixture.exists() and not fixture.is_symlink():
        assert fixture.is_dir() and not any(fixture.iterdir()), 'Only an empty task-owned Docker mountpoint may be replaced'
        fixture.rmdir()
    if not fixture.exists():shutil.copytree(P/'native/fixtures',fixture)
    assert fixture.is_dir() and not fixture.is_symlink()
    shutil.copytree(P/'profile_reference',R/'profile_reference',dirs_exist_ok=True)
    original=VERSIONS/'v234/bin/docker'
    text=original.read_text().replace('HERE = Path(__file__).resolve().parents[1]',
        'HERE = Path('+repr(str(VERSIONS/'v234'))+')')
    old="(PREFIX / 'evidence' / (name + '_adapter.json'))"
    assert text.count(old)==1
    text=text.replace(old,'(Path('+repr(str(R/'evidence'))+") / (name + '_adapter.json'))")
    bins=M/'bin';bins.mkdir(exist_ok=True)
    (bins/'docker').write_text(text)
    for name in ['ffmpeg','ffprobe']:shutil.copy2(VERSIONS/'v234/bin'/name,bins/name)
    for p in bins.iterdir():p.chmod(0o755)
    inputs=json.loads((VERSIONS/'v235/input_identity.json').read_text())['files']
    for rel,digest in inputs.items():assert sha(R/'repo'/rel)==digest,rel
    receipt.write_text(json.dumps(dict(passed=True,physics_steps=0,original_inputs=len(inputs),
        factory_adapter_source_sha256=sha(original),current_adapter_sha256=sha(bins/'docker'),
        factory_bootstrap_read_only='/home/ubuntu/sun/vla_v234_20261017/bootstrap',
        source_manifest_sha256=sha(R/'source/native_manifest.json'),
        runtime_helpers='Separate materialized execution bindings; native sources/install stay frozen.'),indent=2)+'\n')


def freeze():
    target=M/'physical_manifest01.json';assert not target.exists()
    import benchmark,execution_policy
    benchmark.verify();review=execution_policy.verify()
    cases=json.loads((R/'source/native_manifest.json').read_text())['physical_cases']
    preflight=json.loads((R/'evidence/physical_preflights01.json').read_text())
    assert preflight['passed'] and [x['case_id'] for x in preflight['cases']]==cases
    assert all(x['exit_code']==0 and x['physics_steps']==0 for x in preflight['cases'])
    files={}
    def add(p):files[str(p.relative_to(R))]=sha(p)
    inputs=json.loads((VERSIONS/'v235/input_identity.json').read_text())['files']
    for rel,digest in inputs.items():
        p=R/'repo'/rel;assert sha(p)==digest;add(p)
    suffixes={'.py','.cpp','.cc','.h','.hpp','.yaml','.yml','.json','.sh','.xml','.txt','.inc','.gdb'}
    for p in VERSIONS.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix in suffixes:add(p)
    for name in ['physical.py','physical_template.py','batch.py','preflight.py','physical_setup.py','benchmark.py','execution_policy.py']:
        add(M/name)
    for directory in [M/'bin',R/'profile_reference']:
        for p in directory.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:add(p)
    for name in ['native_manifest.json','execution_review.json']:add(R/'source'/name)
    for p in (R/'native/fixtures').rglob('*'):
        if p.is_file():add(p)
    for name in ['complete.json','offline_gate.json','matrix_summary.json','native_ledger.json','audit_ledger.json','selection.json']:
        add(R/'benchmark'/name)
    for name in ['physical_setup01.json','physical_preflights01.json','local_source_return01.json','fixture_paths01.json']:
        add(R/'evidence'/name)
    native=json.loads((R/'source/native_manifest.json').read_text())
    result=dict(version='v290',frozen=True,host='ultra9',physical_cases=cases,authorized_attempts_per_case=1,
        hard_radius_m=.35,sensor_period_s=.1,deadline_s=.1,native_manifest_sha256=sha(R/'source/native_manifest.json'),
        original_policy_sha256=native['policy_sha256'],debug_image='sha256:af529e408d9d130ba7b15a1eb2b78dc7b5408953a0de994ea05cccb43972fbec',
        execution_admission=review,files=files,frozen_utc_s=time.time())
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,manifest_sha256=sha(target),files=len(files))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','freeze'])
    dict(prepare=prepare,freeze=freeze)[p.parse_args().mode]()
