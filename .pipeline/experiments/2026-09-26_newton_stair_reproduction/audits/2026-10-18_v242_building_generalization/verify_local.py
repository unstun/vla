"""Verify returned evidence, stage labels, frozen identity and blocked entry."""
from pathlib import Path
import ast,hashlib,json,math,os,re,subprocess,sys

HERE=Path(__file__).resolve().parent;EXP=HERE.parents[1];V242=EXP/'versions/v242';V243=EXP/'versions/v243'
OUT=HERE/'offline'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    receipt=json.loads((OUT/'RETURN_MANIFEST.json').read_text())
    for name,record in receipt['files'].items():
        p=OUT/name
        assert p.stat().st_size==record['bytes'] and sha(p)==record['sha256'],name
    assert sum(r['bytes'] for r in receipt['files'].values())==receipt['total_bytes']
    manifest=json.loads((V242/'manifest.json').read_text())
    for name,expected in manifest['source_files'].items():
        assert sha(V242/name)==expected,name
        assert sha(V242/manifest['snapshot_locations'][name])==expected,name
    assert sha(V242/'cases_manifest.json')==sha(OUT/'cases_manifest.json')==manifest['cases_manifest_sha256']
    assert sha(V242.parent/'v240/manifest.json')==manifest['parent_manifest_sha256']
    assert sha(V242.parent/'v241/manifest.json')==manifest['historical_control_manifest_sha256']
    cases=json.loads((OUT/'cases_manifest.json').read_text())['cases']
    calls=json.loads((OUT/'matrix_summary.json').read_text())['calls']
    assert len(cases)==12 and len(calls)==60
    assert len({(r['case_id'],r['repetition']) for r in calls})==60
    for case in cases:
        folder=OUT/'cases'/case['case_id'];scenario=json.loads((folder/'scenario.json').read_text())
        assert sha(folder/'scenario.json')==case['scenario_sha256']
        assert scenario['spawn_yaw_rad']==case['start']['yaw']
        values=list(map(float,(folder/'endpoints.txt').read_text().split()))
        expected=case['start']['ground'][:2]+[case['start']['ground'][2]+.3]+case['goal']['ground'][:2]+[case['goal']['ground'][2]+.3,case['start']['yaw']]
        assert len(values)==7 and max(abs(a-b) for a,b in zip(values,expected))<1e-12
        assert {r['repetition'] for r in calls if r['case_id']==case['case_id']}=={1,2,3,4,5}
        fixture=json.loads((folder/'fixture.json').read_text())
        assert fixture['physics_steps']==0 and fixture['captured_state_unchanged'] and fixture['max_scan_s']<=.1
    for row in calls:
        m=row['metrics'];assert row['exit_code']==0
        assert m['pct_plugin_library']=='/work/install/lite3_nav2_plugins/lib/liblite3_nav2_plugins.so'
        assert math.isfinite(m['global_s']) and m['global_s']>=0
        if row['global_admitted']:
            assert m['static_requests']==1 and m['static_rejected_samples']==0
            assert m['scan_rounds']==1 and m['scan_successes']==1 and m['scan_published']==1
            assert m['published_independent_status']==0 and m['stale_inputs_ready']==0
            assert m['body_age_s']==m['cloud_age_s']==0
        else:
            assert m['global_error']=='Native PCT: pct_no_route'
            assert m['static_requests']==m['scan_evaluated']==m['scan_published']==0
    assert sum(r['end_to_end_pass'] for r in calls)==5
    assert {r['case_id'] for r in calls if r['end_to_end_pass']}=={'A02'}
    text=(OUT/'endpoint_inspect02.txt').read_text()
    visits={name:(int(ok),int(n)) for name,ok,n in re.findall(r'REACHABILITY /evaluation/cases/(\w+)/endpoints.txt,reached=(\d+),visited_rows=(\d+)',text)}
    assert len(visits)==12 and visits['A02'][0]==1
    assert all(visits[k]==(0,1) for k in ('A01','A03','G05','G06'))
    assert all(visits[k]==(0,1232) for k in ('A04','G07'))
    assert visits['R11']==(0,46284) and visits['R12']==(0,46290)
    assert all(visits[k]==(0,0) for k in ('B08','B09','R10'))
    selected=json.loads((V243/'selection.json').read_text())
    assert not selected['physical_admission_passed'] and len(selected['selected'])==1
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',V243_CASE_ID='A02')
    result=subprocess.run([sys.executable,str(V243/'launch.py')],env=env,capture_output=True,text=True,timeout=10)
    assert result.returncode!=0 and 'v243 physical launch blocked' in result.stderr
    assert not (V243/'manifest.json').exists()
    assert not list((HERE/'delivered').glob('*.mp4'))
    syntax=0
    for root in (V242,V243,HERE):
        for p in root.rglob('*.py'):ast.parse(p.read_text(),str(p));syntax+=1
        for p in root.rglob('*'):
            if p.is_file():
                assert p.suffix not in ('.pyc','.o','.a','.so','.npz','.zip','.f32','.pct'),p
                assert 'CMakeFiles' not in p.parts and '__pycache__' not in p.parts,p
    quality=dict(offline_implementation_checks_passed=True,generalization_coverage_gate_passed=False,
        returned_files_verified=len(receipt['files']),returned_bytes=receipt['total_bytes'],
        frozen_source_and_snapshot_identity_passed=True,scored_calls_verified=60,
        native_positive_and_stale_controls_passed=True,precise_phase_and_search_ledger_verified=True,
        blocked_physical_entry_test_passed=True,blocked_entry_exit_code=result.returncode,
        python_syntax_files=syntax,physical_attempts=0,physical_qualified=False,
        v243_unexecuted=['native graph preflight','physical route','physical metrics','video rendering/QA'],
        claim='Evidence integrity and adapter controls pass; endpoint coverage and physical admission fail')
    (HERE/'QUALITY.json').write_text(json.dumps(quality,indent=2)+'\n')
    print(json.dumps(quality,indent=2))

if __name__=='__main__':main()
