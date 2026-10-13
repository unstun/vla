"""Exercise actual entry source/native/qualification gates without launching physics."""
from pathlib import Path
import argparse,ast,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];ROOT=BASE.parents[2]
assert str(ROOT)=='/home/sun/vla_exec/vla'
p=argparse.ArgumentParser();p.add_argument('--before-freeze',action='store_true');a=p.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('actual_entry',HERE/'run_local_episode.py');entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
manifest=json.loads((BASE/'versions/v57/manifest.json' if a.before_freeze else HERE/'manifest.json').read_text())
assert all(sha(ROOT/n)==h for n,h in manifest['source_files'].items())
entry.verify_native_build(entry.BUILD,manifest)
q=json.loads((HERE/'component_qualification.json').read_text());tree=ast.parse((HERE/'run_local_episode.py').read_text());keys=sorted({n.slice.value for n in ast.walk(tree) if isinstance(n,ast.Subscript) and isinstance(n.value,ast.Name) and n.value.id=='qualification' and isinstance(n.slice,ast.Constant) and isinstance(n.slice.value,str)})
assert keys and all(q[k] is True for k in keys)
result=json.loads((HERE/'tests/attempt02/result.json').read_text());assert q['test_result_sha256']==sha(HERE/'tests/attempt02/result.json') and result['endpoint_evidence_passed']
info=json.loads((HERE/'physical_floor_input.json').read_text());assert sha(HERE/'assets/physical_floor.f32')==info['files']['physical_floor.f32']['sha256']
out=HERE/('entry_gate_before_freeze.json' if a.before_freeze else 'entry_gate_frozen.json');out.write_text(json.dumps({'entry_source_sha256':sha(HERE/'run_local_episode.py'),'qualification_sha256':sha(HERE/'component_qualification.json'),'required_legacy_keys':keys,'all_keys_derived_and_passed':True,'actual_native_source_install_gate_passed':True,'exact_physical_asset_passed':True,'source_files_verified':len(manifest['source_files']),'physics_launched':False},indent=2)+'\n');print(out.read_text())
