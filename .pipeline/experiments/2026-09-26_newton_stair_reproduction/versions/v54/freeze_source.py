"""Freeze qualified v54 component source; inherited identical bytes stay referenced."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4];BASE=HERE.parents[1]
NATIVE=BASE/'runtime/scan76_warm_clock_guard_v54'
PARENT_NATIVE=BASE/'runtime/scan75_reference_continuity_v53'
PARENT_VERSION='v53'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    assert not (HERE/'manifest.json').exists(),'Frozen versions are immutable'
    parent_path=HERE.parent/PARENT_VERSION/'manifest.json';parent=json.loads(parent_path.read_text())
    selected=dict(parent['source_files']);locations=dict(parent['snapshot_locations'])
    assert all(sha(ROOT/n)==h and sha(ROOT/locations[n])==h for n,h in selected.items())
    qualification=json.loads((HERE/'component_qualification.json').read_text());assert qualification['component_passed']
    assert qualification['physics_run'] is False
    native=json.loads((NATIVE/'source_sha256.json').read_text());assert all(sha(NATIVE/n)==h for n,h in native.items())
    assert json.loads((NATIVE/'build_result.json').read_text())['passed']
    own=[p for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.md','.yaml','.json','.patch') and p.name not in ('manifest.json','execution_copy_verification.json')]
    for directory in ('backend_ros','contract','corner'):
        own.extend(p for p in (HERE/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and not any(x.startswith(('attempt','red')) for x in p.relative_to(HERE/directory).parts[:-1]))
    own.extend(NATIVE/n for n in native)
    own.extend(NATIVE/n for n in ('source_sha256.json','install_sha256.json','build_result.json'))
    copied=0
    for p in sorted(set(own)):
        name=str(p.relative_to(ROOT));digest=sha(p)
        if p.is_relative_to(NATIVE): inherited=PARENT_NATIVE/p.relative_to(NATIVE)
        elif p.is_relative_to(HERE): inherited=HERE.parent/PARENT_VERSION/p.relative_to(HERE)
        else: inherited=None
        previous=str(inherited.relative_to(ROOT)) if inherited else ''
        if previous in parent['source_files'] and parent['source_files'][previous]==digest:
            location=parent['snapshot_locations'][previous]
        else:
            destination=HERE/'source'/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,destination);location=str(destination.relative_to(ROOT));copied+=1
        selected[name]=digest;locations[name]=location
        assert sha(ROOT/location)==digest
    manifest={'version':HERE.name,'parent':PARENT_VERSION,'native_source_parent':PARENT_VERSION,'parent_manifest_sha256':sha(parent_path),'status':'frozen_components_passed_physics_pending','source_files':dict(sorted(selected.items())),'snapshot_locations':dict(sorted(locations.items())),'snapshot_storage':'Unchanged bytes refer to the frozen parent; this version owns only its delta','native_source_sha256':native,'native_install_sha256':json.loads((NATIVE/'install_sha256.json').read_text()),'physics_run':False,'full_stack_integrated':False,'navigation_validated':False}
    (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'version':HERE.name,'frozen_files':len(selected),'copied_delta_files':copied,'navigation_validated':False}))
if __name__=='__main__':main()
