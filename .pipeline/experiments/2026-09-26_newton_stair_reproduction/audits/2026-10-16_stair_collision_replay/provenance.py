"""Record executed audit sources, native binaries and compact result hashes."""
from pathlib import Path
import hashlib
import json
ROOT=Path('/data/sun/vla_mppi_20261009/stair_collision_replay_20261016')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((ROOT/'source/source_manifest.json').read_text())
for name,expected in manifest.items():assert sha(ROOT/'source'/name)==expected,name
source={str(p.relative_to(ROOT/'source')):sha(p) for p in (ROOT/'source').rglob('*') if p.is_file() and '__pycache__' not in str(p) and p.suffix not in ('.pyc',)}
reference={str(p.relative_to(ROOT/'reference')):sha(p) for p in (ROOT/'reference').rglob('*') if p.is_file()}
binaries={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'build/collision_probe',ROOT/'build/support_probe',ROOT/'build_original/original_probe']}
libraries={}
for prefix in ['command_continuity_v206_20261015','starvation_recovery_v219']:
    for p in (ROOT.parent/prefix/'install').glob('plan_env/lib/*'):
        if p.is_file():libraries[str(p)]=sha(p)
assert libraries,'Expected the frozen native map archive'
inputs={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'input/identity.json',ROOT/'critical_input/identity.json',ROOT/'input/planner.yaml',ROOT/'input/terrain.json']}
logs={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'logs').glob('*.log')}
result={'host':'gpu5070ti','remote_root':str(ROOT),'environment':json.loads((ROOT/'environment.json').read_text()),'audit_sources':source,'reference_files':reference,'binaries':binaries,'installed_plan_env_libraries':libraries,'native_link_command':(ROOT/'build/CMakeFiles/collision_probe.dir/link.txt').read_text(),'input_receipts':inputs,'logs':logs,'final_video':json.loads((ROOT/'output/video_final02/verification.json').read_text()),'failures_preserved':['Initial preview omitted required output argument','First preview encountered unsupported tuple color in renderer','First exact-query execution had host-absolute links unavailable in container; corrected to relative links'],'auxiliary_log_boundary':'input/rejection_log.json is an exploratory excerpt indexed by preceding sampled frame, not event time; actual failures use critical_input log text and now/body stamps.','physics_steps':0,'navigation_source_edits':False}
(ROOT/'output/provenance.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'audit_files':len(source),'reference_files':len(reference),'binaries':binaries,'libraries':libraries},indent=2))
