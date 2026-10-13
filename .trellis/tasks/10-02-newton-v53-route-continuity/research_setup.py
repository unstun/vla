from pathlib import Path
import hashlib,json,shutil
B=Path('.pipeline/experiments/2026-09-26_newton_stair_reproduction')
N=B/'runtime/scan75_reference_continuity_v53'; P=B/'runtime/scan74_terrain_lookup_v52'; V=B/'versions/v53'; Q=B/'versions/v52'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
frozen=json.loads((Q/'manifest.json').read_text())
assert all(sha(P/n)==h for n,h in frozen['native_source_sha256'].items())
assert not N.exists() and not V.exists()
shutil.copytree(P/'src',N/'src');V.mkdir()
files=['remote_build.py','remote_test.py','remote_trial.py','analyze_trial.py','test_backend_contract.py','building_planner.yaml','controller.yaml']+list(json.loads((Q/'runtime_preparation.json').read_text())['files'])
rows={}
for name in files:
    src=Q/name; data=src.read_bytes()
    if name in ['remote_build.py','remote_test.py','remote_trial.py','analyze_trial.py','run_local_episode.py','native_graph.py','navigation_contract.json']:
        data=data.replace(b'scan74_terrain_lookup_v52',b'scan75_reference_continuity_v53').replace(b'scan74-terrain-lookup-v52',b'scan75-reference-continuity-v53').replace(b'v52',b'v53')
    (V/name).write_bytes(data)
    rows[name]={'parent_sha256':sha(src),'output_sha256':sha(V/name)}
# Build inheritance is v52; BUILD_TESTING and physics settings remain unchanged.
p=V/'remote_build.py';p.write_text(p.read_text().replace('runtime/scan73_v48_continuity_v50','runtime/scan74_terrain_lookup_v52'))
for name in ['contract','backend_ros']:
    shutil.copytree(Q/name,V/name,ignore=shutil.ignore_patterns('__pycache__'))
# Preserve historical contract marker names; these gates test unchanged features.
(V/'runtime_preparation.json').write_text(json.dumps({'parent':'v52','files':{n:rows[n] for n in json.loads((Q/'runtime_preparation.json').read_text())['files']}},indent=2)+'\n')
(V/'preparation.json').write_text(json.dumps({'version':'v53','parent':'v52','parent_manifest_sha256':sha(Q/'manifest.json'),'native_source_parent_sha256':sha(P/'source_sha256.json'),'status':'unfrozen_candidate'},indent=2)+'\n')
(V/'PLAN.md').write_text('# v53 compatible route refresh\n\nApproved 2026-10-02. Parent: frozen v52. Implements D1 in the approved Trellis corner-continuity design. Component qualification precedes freeze; physics follows the v54/v55 chain. No planner deadline or stop changes.\n')
T=Path('.trellis/tasks/10-02-newton-v53-route-continuity/task.json'); t=json.loads(T.read_text());t['notes']='Latest parent plan approved by Dr Sun: ok. Implementation started inline, experiment + analysis stage.';T.write_text(json.dumps(t,indent=2)+'\n')
# New replay source compiles against either frozen parent or candidate. Red uses parent unchanged.
A=B/'audits/2026-10-02_v52_corner_43s'; R=V/'corner';R.mkdir()
for name in ['corner_replay.cpp','CMakeLists.txt','prepare_replay.py']:
    shutil.copyfile(A/name,R/name)
inside=(A/'inside.sh').read_text().replace('python3 /profile/prepare_replay.py > /attempt/conversion.log 2>&1','mkdir -p /attempt/replay\nln -s /archive/audits/2026-10-02_v52_corner_43s/attempt05/replay/events.bin /attempt/replay/events.bin')
(R/'inside.sh').write_text(inside)
p=R/'corner_replay.cpp';s=p.read_text();s=s.replace('if(id==0){','if(id==1){ if(saved_red_placeholder){} }\n   if(id==0){',1) if False else s
# Test result records callback-cleared binding directly; parent red fails the approved expectation.
s=s.replace('const auto saved_local=manager.local_data_;','if(id==1) results << "{\\\"kind\\\":\\\"refresh_binding\\\",\\\"retained\\\":" << (manager.accepted_warm_traj_id_==manager.local_data_.traj_id_ && fsm.feasible_window_.valid) << "}\\n";\n   const auto saved_local=manager.local_data_;',1)
p.write_text(s)
# Remote wrapper versions parent paths and output identity, with separate red/candidate modes.
s=(A/'remote_replay.py').read_text().replace('BASE = HERE.parents[1]','BASE = HERE.parents[2]').replace("out = HERE/'attempt05'","parser = __import__('argparse').ArgumentParser(); parser.add_argument('--parent-red',action='store_true');parser.add_argument('--attempt',type=int,default=1);args=parser.parse_args()\n    global NATIVE\n    if not args.parent_red: NATIVE = BASE/'runtime/scan75_reference_continuity_v53'\n    out = HERE/(f'red{args.attempt:02d}' if args.parent_red else f'attempt{args.attempt:02d}')").replace('vla-v52-corner-20261002','vla-v53-corner-20261002').replace("str(BASE/'versions/v52')","str(BASE/'versions/v53')")
# Do not promote completed replay to a passing regression unless its expected outcome holds.
s=s.replace("result=dict(exit_code=code", "retained=next((bool(p['retained']) for p in probes if p.get('kind')=='refresh_binding'),False)\n    result=dict(expected_refresh_binding=retained, parent_red=args.parent_red, exit_code=code")
s=s.replace("if result['completed'] and unchanged else 1", "if result['completed'] and unchanged and (not retained if args.parent_red else retained) else 1")
(R/'remote_replay.py').write_text(s)
manifest={str(p.relative_to(N)):sha(p) for p in (N/'src').rglob('*') if p.is_file()};(N/'source_sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'parent_verified':len(manifest),'new_native':str(N),'new_version':str(V)}))
