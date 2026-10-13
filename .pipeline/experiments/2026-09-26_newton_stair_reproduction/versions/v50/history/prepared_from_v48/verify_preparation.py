"""Verify the untouched v48 branch and frozen-v49 preservation; not a runtime test."""
from pathlib import Path
import ast,hashlib,json
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
ROOT=BASE.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parent=json.loads((HERE/'parent_identity.json').read_text());assert parent['parent']==parent['version']==parent['native_source_parent']=='v48'
 assert sha(HERE.parent/'v48/manifest.json')==parent['manifest_sha256']
 old=BASE/'runtime/scan71_remaining_curve_v48';new=BASE/'runtime/scan73_v48_continuity_v50';expected=parent['native_source_sha256']
 actual={str(p.relative_to(new)):sha(p) for p in (new/'src').rglob('*') if p.is_file()}
 assert actual==expected
 assert all(sha(old/name)==digest for name,digest in expected.items())
 assert not (new/'src/plan_env/include/plan_env/planning_deadline.h').exists()
 required=['run_local_episode.py','native_graph.py','native_backend_entry.py','navigation_contract.json','newton_episode.py','realtime_pacer.py','frequency_observer.py']
 assert all((HERE/name).is_file() for name in required)
 for p in HERE.glob('*.py'):ast.parse(p.read_text())
 same=[]
 for name in ('building_planner.yaml','flat_planner.yaml','controller.yaml'):
  assert (HERE/name).read_bytes()==(HERE.parent/'v48'/name).read_bytes();same.append(name)
 for p in (HERE.parent/'v48/backend_ros').rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts:
   relative=p.relative_to(HERE.parent/'v48');assert sha(HERE/relative)==sha(p);same.append(str(relative))
 child=json.loads((HERE/'navigation_contract.json').read_text());source=json.loads((HERE.parent/'v48/navigation_contract.json').read_text());source['version']='v50';assert child==source
 preserved=json.loads((HERE/'v49_preservation.json').read_text());r=HERE.parent/'v49'
 for name,digest in preserved['version_directory_files'].items():assert sha(r/name)==digest,name
 assert sha(r/'manifest.json')==preserved['v49_manifest_sha256']
 assert json.loads((r/'acceptance_result.json').read_text())['accepted'] is False
 # Launch wrapper is the original parent behavior, adapted only to v50 identity.
 assert (HERE/'native_graph.py').read_text()==(HERE.parent/'v48/native_graph.py').read_text().replace('v48','v50')
 result={'parent':'v48','native_files_exact':len(actual),'unchanged_config_backend_files':len(same),'v49_files_unchanged':len(preserved['version_directory_files']),'required_launch_files_present':required,'navigation_contract_change':'version label only','new_timing_policy':False,'built':False,'runtime_tested':False,'validated':False}
 (HERE/'preparation_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
