from pathlib import Path
import hashlib,json,shutil
B=Path('.pipeline/experiments/2026-09-26_newton_stair_reproduction');Q=B/'versions/v53';V=B/'versions/v54';P=B/'runtime/scan75_reference_continuity_v53';N=B/'runtime/scan76_recovery_freshness_v54'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=json.loads((Q/'manifest.json').read_text());assert all(sha(P/n)==h for n,h in m['native_source_sha256'].items());assert not N.exists() and not V.exists();V.mkdir();shutil.copytree(P/'src',N/'src')
files=['remote_build.py','remote_test.py','remote_trial.py','analyze_trial.py','test_backend_contract.py','building_planner.yaml','controller.yaml','freeze_source.py','materialize.py']+list(json.loads((Q/'runtime_preparation.json').read_text())['files']);rows={}
for name in files:
    src=Q/name;data=src.read_bytes()
    if name in ['remote_build.py','remote_test.py','remote_trial.py','analyze_trial.py','run_local_episode.py','native_graph.py','navigation_contract.json','freeze_source.py','materialize.py']:
        data=data.replace(b'scan75_reference_continuity_v53',b'scan76_recovery_freshness_v54').replace(b'scan75-reference-continuity-v53',b'scan76-recovery-freshness-v54').replace(b'v53',b'v54')
    (V/name).write_bytes(data);rows[name]={'parent_sha256':sha(src),'output_sha256':sha(V/name)}
for name in ['contract','backend_ros']:
    shutil.copytree(Q/name,V/name,ignore=shutil.ignore_patterns('__pycache__'))
p=V/'remote_build.py';p.write_text(p.read_text().replace('PARENT = BASE / "runtime/scan74_terrain_lookup_v52"','PARENT = BASE / "runtime/scan75_reference_continuity_v53"'))
p=V/'freeze_source.py';s=p.read_text().replace("PARENT_NATIVE=BASE/'runtime/scan74_terrain_lookup_v52'","PARENT_NATIVE=BASE/'runtime/scan75_reference_continuity_v53'").replace("PARENT_VERSION='v52'","PARENT_VERSION='v53'");p.write_text(s)
p=V/'materialize.py';p.write_text(p.read_text().replace('runtime/scan74_terrain_lookup_v52','runtime/scan75_reference_continuity_v53').replace('versions/v52/manifest.json','versions/v53/manifest.json'))
(V/'runtime_preparation.json').write_text(json.dumps({'parent':'v53','files':{n:rows[n] for n in json.loads((Q/'runtime_preparation.json').read_text())['files']}},indent=2)+'\n')
(V/'preparation.json').write_text(json.dumps({'version':'v54','parent':'v53','parent_manifest_sha256':sha(Q/'manifest.json'),'native_source_parent_sha256':sha(P/'source_sha256.json'),'status':'unfrozen_candidate'},indent=2)+'\n')
(V/'PLAN.md').write_text('# v54 recovery freshness\n\nApproved 2026-10-02. Parent: qualified frozen v53. Implements D2 of the reviewed corner-continuity design. Drain existing queued body/sensor inputs before prefix endpoint admission, preserving fixed start PVA, callback order and 0.25 s cloud limit. No planner deadline, stop or threshold changes.\n')
(N/'source_sha256.json').write_text(json.dumps({str(p.relative_to(N)):sha(p) for p in (N/'src').rglob('*') if p.is_file()},indent=2)+'\n')
# Distinct corner sources for final component replay; no bulk fixtures copied locally.
R=V/'corner';R.mkdir()
for name in ['corner_replay.cpp','CMakeLists.txt','inside.sh','remote_replay.py']:
    data=(Q/'corner'/name).read_bytes().replace(b'scan75_reference_continuity_v53',b'scan76_recovery_freshness_v54').replace(b'v53',b'v54');(R/name).write_bytes(data)
p=R/'remote_replay.py';p.write_text(p.read_text().replace("NATIVE = BASE / 'runtime/scan74_terrain_lookup_v52'","NATIVE = BASE / 'runtime/scan75_reference_continuity_v53'"))
T=Path('.trellis/tasks/10-02-newton-v53-route-continuity/task.json');t=json.loads(T.read_text());t.update(status='completed',completedAt='2026-10-02',notes='v53 component build/contracts/callback replay qualified and frozen. Integrated reserve/corner/30 Hz physics remains with parent task.');T.write_text(json.dumps(t,indent=2)+'\n')
T=Path('.trellis/tasks/10-02-newton-v54-recovery-freshness/task.json');t=json.loads(T.read_text());t['notes']='Approved D2 started after qualified frozen v53; physics integration pending parent task.';t['meta']['qualified_parent_manifest_sha256']=sha(Q/'manifest.json');T.write_text(json.dumps(t,indent=2)+'\n')
print(json.dumps({'version':'v54','parent':'v53','parent_verified':100}))
