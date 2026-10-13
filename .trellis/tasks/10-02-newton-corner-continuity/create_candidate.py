"""Create a source-only integer candidate after predecessor component freeze."""
from pathlib import Path
import argparse,hashlib,json,shutil,re
parser=argparse.ArgumentParser();parser.add_argument('--version',required=True);parser.add_argument('--parent',required=True);parser.add_argument('--native',required=True);parser.add_argument('--parent-native',required=True);a=parser.parse_args()
B=Path('.pipeline/experiments/2026-09-26_newton_stair_reproduction');Q=B/'versions'/a.parent;V=B/'versions'/a.version;P=B/'runtime'/a.parent_native;N=B/'runtime'/a.native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=json.loads((Q/'manifest.json').read_text());assert json.loads((Q/'component_qualification.json').read_text())['component_passed'];assert all(sha(P/n)==h for n,h in m['native_source_sha256'].items());assert not N.exists() and not V.exists();V.mkdir();shutil.copytree(P/'src',N/'src')
runtime=json.loads((Q/'runtime_preparation.json').read_text())['files'];files=['remote_build.py','remote_test.py','remote_trial.py','analyze_trial.py','test_backend_contract.py','building_planner.yaml','controller.yaml','freeze_source.py','materialize.py']+list(runtime);rows={}
for name in files:
    src=Q/name;data=src.read_bytes()
    if name in ['remote_build.py','remote_test.py','remote_trial.py','analyze_trial.py','run_local_episode.py','native_graph.py','navigation_contract.json','freeze_source.py','materialize.py']:
        data=data.replace(a.parent_native.encode(),a.native.encode()).replace(a.parent.encode(),a.version.encode())
    (V/name).write_bytes(data);rows[name]={'parent_sha256':sha(src),'output_sha256':sha(V/name)}
for name in ['contract','backend_ros']:
    shutil.copytree(Q/name,V/name,ignore=shutil.ignore_patterns('__pycache__'))
p=V/'remote_build.py';s=p.read_text();s=re.sub(r'PARENT = BASE / "[^"]+"',f'PARENT = BASE / "runtime/{a.parent_native}"',s);s=re.sub(r'builder.NAME = "[^"]+"',f'builder.NAME = "vla-build-{a.native.replace("_","-")}"',s);p.write_text(s)
p=V/'freeze_source.py';s=p.read_text();s=re.sub(r"PARENT_NATIVE=BASE/'[^']+'",f"PARENT_NATIVE=BASE/'runtime/{a.parent_native}'",s);s=re.sub(r"PARENT_VERSION='[^']+'",f"PARENT_VERSION='{a.parent}'",s);p.write_text(s)
p=V/'materialize.py';s=p.read_text();s=re.sub(r"PARENT=BASE/'[^']+'",f"PARENT=BASE/'runtime/{a.parent_native}'",s);s=re.sub(r"parent=BASE/'versions/[^']+/manifest.json'",f"parent=BASE/'versions/{a.parent}/manifest.json'",s);p.write_text(s)
(V/'runtime_preparation.json').write_text(json.dumps({'parent':a.parent,'files':{n:rows[n] for n in runtime}},indent=2)+'\n')
(V/'preparation.json').write_text(json.dumps({'version':a.version,'parent':a.parent,'parent_manifest_sha256':sha(Q/'manifest.json'),'native_source_parent_sha256':sha(P/'source_sha256.json'),'status':'unfrozen_candidate'},indent=2)+'\n')
(N/'source_sha256.json').write_text(json.dumps({str(p.relative_to(N)):sha(p) for p in (N/'src').rglob('*') if p.is_file()},indent=2)+'\n')
R=V/'corner';R.mkdir()
for name in ['corner_replay.cpp','CMakeLists.txt','inside.sh','remote_replay.py']:
    data=(Q/'corner'/name).read_bytes().replace(a.parent_native.encode(),a.native.encode()).replace(a.parent.encode(),a.version.encode());(R/name).write_bytes(data)
p=R/'remote_replay.py';s=p.read_text();s=re.sub(r"^NATIVE = BASE / '[^']+'",f"NATIVE = BASE / 'runtime/{a.parent_native}'",s,flags=re.M);p.write_text(s)
print(json.dumps({'version':a.version,'parent':a.parent,'parent_verified':100}))
