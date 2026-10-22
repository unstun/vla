"""Verify unchanged frozen inputs and exactly ten consumed recordings, no new physics."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
R=Path('/home/ubuntu/sun/vla_v290_20261021')
P=Path('/home/ubuntu/sun/vla_v289_20261020')
E=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
os.environ.setdefault('V290_CASE_ID','A04');sys.path.insert(0,str(R/'migration'))
import physical
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=physical.verify_sources()
complete=json.loads((R/'evidence/physical_batch_complete.json').read_text())
rows=json.loads(Path(complete['status_source']).read_text())
assert len(rows)==10 and all(r['stage']=='closed' and r['physics_steps']>0 for r in rows)
assert complete['all_closed'] and complete['positive_physics_recordings']==10
assert len(list((R/'physical_runs').glob('v290_*_attempt01')))==10
status=json.loads((R/'evidence/analysis_batch_status.json').read_text())
assert len(status)==10 and all(r['passed'] for r in status)
names=subprocess.check_output(['docker','ps','--format','{{.Names}}'],text=True).splitlines()
owned=[n for n in names if n.startswith('v290-')];assert not owned,owned
parent=P/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v289/native_manifest.json'
assert sha(parent)=='5406c3d4930c29d4bb4a456c43874963c236ab9de2ef7fc9ae2c27a60b5f1d06'
parent_data=json.loads(parent.read_text());verified=0
for rel,value in parent_data['files'].items():
    expected=value if isinstance(value,str) else value['sha256']
    assert sha(parent.parent/rel)==expected,rel
    verified+=1
result=dict(passed=True,physics_steps=0,script_sha256=sha(Path(__file__)),source_verification=proof,
    parent_manifest_sha256=sha(parent),parent_files_verified=verified,physical_attempts=10,
    positive_physics_steps_lower_bound=sum(r['physics_steps'] for r in rows),
    incomplete_recordings=complete['incomplete_recordings'],active_owned_containers=owned,
    other_containers_left_running=len(names),disk_free_gib=shutil.disk_usage(R).free/2**30,
    hard_radius_m=.35,sensor_period_s=.1,physics_reruns_for_analysis=0,verified_utc_s=time.time())
out=R/'evidence/final_frozen_sources01.json';assert not out.exists()
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='source_verification'}))
