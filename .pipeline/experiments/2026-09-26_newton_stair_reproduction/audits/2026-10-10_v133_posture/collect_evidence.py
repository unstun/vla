"""Return allowlisted compact evidence and rehash retained raw files remotely."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];TASK=Path('/data/sun/vla_mppi_20261009')
def sha(path):
    d=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024**2),b''):d.update(chunk)
    return d.hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--attempt',type=int,required=True);a=p.parse_args()
    assert not subprocess.check_output(['docker','ps','--format','{{.Names}}'],text=True).strip()
    out=TASK/f'results/posture_return_{a.attempt:02d}';out.mkdir(exist_ok=False)
    selected=[];raw=[];identities=[]
    original_index=TASK/'results/recovery_v133/comparison/v133_candidate_attempt02/remote_artifacts.json'
    assert sha(original_index)=='231952aca880d4c0bfa8ae18a09078222428cf60c9ce490c60badca88edc62b6'
    original=json.loads(original_index.read_text())
    for name,expected in original['files'].items():
        path=Path(original['root'])/name
        assert path.stat().st_size==expected['bytes'] and sha(path)==expected['sha256'],str(path)
    selected.append(original_index)
    for version in ['v134','v135','v136','v137','v138','v139']:
        v=BASE/'versions'/version
        quality=json.loads((v/'quality.json').read_text())
        selected.extend(Path(d['path']) for d in quality['checks'].values())
        identities.append(json.loads(subprocess.check_output([sys.executable,str(v/'freeze_host.py'),'verify'],text=True)))
        root=TASK/'results'/('recovery_'+version+('_02' if version=='v139' else ''))
        for name in ['baseline_receipt.json','candidate_receipt.json']:
            receipt=json.loads((root/name).read_text())
            for path,expected in receipt['files'].items():assert sha(TASK/Path(path).relative_to('/task'))==expected,path
        for f in root.rglob('*'):
            if f.is_file() and f.suffix in ['.json','.csv','.log','.sh'] and 'build' not in f.parts:
                selected.append(f)
                if f.name=='remote_artifacts.json':
                    record=json.loads(f.read_text());trial=Path(record['root'])
                    run=trial/'runs'/trial.name
                    for leaf in ['selected_route_map.json','backend_config.json','episode_request.json','state_copyback.json']:
                        if (run/leaf).is_file():selected.append(run/leaf)
                    if version in ('v135','v136','v137','v138','v139'):
                        chosen=json.loads((run/'selected_route_map.json').read_text())
                        expected=(json.loads((v/'global_map_input.json').read_text())['map_sha256']
                            if version in ('v136','v137','v138','v139') or '_candidate_' in trial.name else 'ab5499ff100fe233f6cfabb59ce7592290cddd042c92ead5e37e9e2b593d24da')
                        assert chosen['sha256']==expected,trial.name
                    for name,expected in record['files'].items():
                        actual=trial/name;assert actual.stat().st_size==expected['bytes'] and sha(actual)==expected['sha256'],str(actual)
                    raw.append({'trial':trial.name,'files':len(record['files']),
                        'bytes':sum(x['bytes'] for x in record['files'].values()),'index_sha256':sha(f),'verified':True})
        for label in ['pilots','repeats']:
            root=TASK/'results'/f'recovery_{version}{"_02" if version=="v139" else ""}_{label}'
            if root.exists():selected.extend(f for f in root.rglob('*') if f.is_file() and f.suffix in ['.json','.csv','.log'])
    for relative in ['results/v133_posture','results/v135_routecheck','results/support_coverage_contract','results/mission_inbox_contract','results/fresh_admission_contract','results/body_envelope_contract','results/sampled_rebound_contract','results/recovery_v139']:
        root=TASK/relative
        selected.extend(f for f in root.rglob('*') if f.is_file() and f.suffix in ['.json','.png','.log','.csv'] and 'build' not in f.parts and 'ros_logs' not in f.parts)
    for relative,names in [
        ('recovery_v139',['source_identity.json']),
        ('support_coverage_v134',['receipt.json','generator_tests.json','mask_test.log']),
        ('global_coverage_v135',['receipt.json']),
        ('global_coverage_v135_foxy',['receipt.json','pct_result.json']),
        ('results',['posture_geometry01.log','diagnostic_dependencies.log','support_coverage_v134.log','support_coverage_prepare.log','support_coverage_prepare02.log','v135_pct_probe.log','v135_pct_probe02.log','mission_inbox_prepare.log','fresh_admission_prepare.log','body_envelope_prepare.log'])]:
        selected.extend(TASK/relative/n for n in names if (TASK/relative/n).is_file())
    manifest={}
    for f in sorted(set(selected)):
        assert f.stat().st_size<3*1024**2,('unexpected large compact artifact',str(f))
        name=str(f.relative_to(TASK));destination=out/name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(f,destination);manifest[name]={'bytes':f.stat().st_size,'sha256':sha(f)}
        assert sha(destination)==manifest[name]['sha256']
    result={'source_identities':identities,'raw_trials':raw,'files':manifest,
        'original_failed_trial_reverified':{'run':'v133_candidate_attempt02','index_sha256':sha(original_index),'files':len(original['files'])},
        'script_sha256':sha(Path(__file__)),'heavy_storage_root':str(TASK),
        'claim':'Source/native input identities and raw bytes verified; navigation conclusions are separate.'}
    (out/'MANIFEST.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'output':str(out),'files':len(manifest),'bytes':sum(f['bytes'] for f in manifest.values()),'raw_trials':len(raw),'manifest_sha256':sha(out/'MANIFEST.json')}))
if __name__=='__main__':main()
