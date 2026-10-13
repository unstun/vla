"""Bind the first completed v177 episode to a full causal review video."""
from pathlib import Path
import hashlib,json,subprocess,sys

H=Path(__file__).resolve().parent;B=H.parents[1];T=Path('/data/sun/vla_mppi_20261009')

def sha(p):
    digest=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024**2),b''):digest.update(chunk)
    return digest.hexdigest()

def main():
    assert H.is_relative_to(T/'repo')
    # Every physical repetition must be closed before any render preparation.
    for attempt in range(1,6):
        trial=f'v177_full_candidate_attempt{attempt:02d}'
        assert (T/'trials'/trial/'evidence/execution.json').is_file(),trial
        assert json.loads((T/'results/v177_full_repeats'/trial/'outcome.json').read_text())['closed']
    tag='v177_full_candidate_attempt01';source=T/'trials'/tag/'runs'/tag
    analysis=T/'results/v177_full_repeats'/tag
    outcome=analysis/'outcome.json';route=analysis/'full_route_verification.json'
    assert json.loads(outcome.read_text())['full_qualification']
    assert json.loads(route.read_text())['passed']
    proof=json.loads((source/'initial_state.json').read_text())
    assert proof['passed'] and proof['physics_time_s']==0.0 and proof['physics_steps']==0
    assert json.loads((source/'video_states.json').read_text())[0]==proof['frame']
    metrics=json.loads((analysis/'metrics.json').read_text())
    assert metrics['terminal']['backend_terminal_status']=='FINISHED' and not metrics['fallen'] and metrics['state_copyback_verified']
    root=T/'video_v178';root.mkdir(exist_ok=False);(root/'runs').mkdir();(root/'cache').mkdir()
    for name in ['test_overlay.py','test_timeline.py']:
        subprocess.run([sys.executable,str(H/name)],check=True)
    inputs=[route,outcome,analysis/'metrics.json',analysis/'latency.csv']
    inputs += [source/name for name in ['initial_state.json','video_states.json','factory_video_states.json',
        'startup_pacing.json','raw_capture.zip','clock_samples.jsonl','backend_states.jsonl',
        'episode_request.json','inputs/stair_scenario.json']]
    identity=json.loads((H/'source_identity.json').read_text())
    for name,expected in identity['files'].items():assert sha(H/name)==expected,name
    contract={'physical_source_root':str(source),'physical_source_run':tag,
        'route_verification':str(route),'analysis_metrics':str(analysis/'metrics.json'),
        'latency_csv':str(analysis/'latency.csv'),
        'parent_manifests':{v:sha(B/'versions'/v/'manifest.json') for v in ['v148','v177']},
        'input_files':{str(p):sha(p) for p in inputs},
        'display_source_identity_sha256':sha(H/'source_identity.json'),'source_outcome_sha256':sha(outcome),
        'claim':'Display only. Complete original-start v177 attempt01, all pauses and recoveries retained. No physics steps. Cohort results reported separately.'}
    (root/'display_contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    print(json.dumps({'prepared':True,'root':str(root),'source':tag,'inputs':len(inputs),'contract_sha256':sha(root/'display_contract.json')}))

if __name__=='__main__':main()
