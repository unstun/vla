from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil,time
R=Path('/home/ubuntu/sun/vla_v288_20261020');E=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction';M=R/'migration'
os.environ.setdefault('V288_CASE_ID','A04');sys.path.insert(0,str(M));import physical
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=physical.verify_sources();parents={}
for version in ['v283','v284','v285','v286','v287','v288']:
 p=E/'versions'/version;manifest=json.loads((p/'native_manifest.json').read_text())
 present=[];missing=[]
 for rel,h in manifest['source_files'].items():
  if not (p/rel).is_file():missing.append(rel);continue
  assert sha(p/rel)==h,(version,rel);present.append(rel)
 if version=='v288':assert not missing,missing
 parents[version]=dict(manifest_sha256=sha(p/'native_manifest.json'),present_source_files_verified=len(present),older_reference_files_not_transferred=missing)
rows=json.loads((R/'evidence/physical_batch_status.json').read_text());assert len(rows)==10 and all(r['stage']=='closed' and r['physics_steps']>0 for r in rows)
assert json.loads((R/'evidence/physical_batch_complete.json').read_text())['positive_physics_recordings']==10
assert json.loads((R/'evidence/after_physics01.json').read_text())['returncode']==0
names=subprocess.check_output(['docker','ps','--format','{{.Names}}'],text=True).splitlines();owned=[n for n in names if n.startswith('v288-')];assert not owned,owned
result=dict(passed=True,verification_script_sha256=sha(Path(__file__)),older_reference_scope='Transferred older files only; complete older source snapshots are verified in the local source-of-truth repository',source_verification=proof,frozen_version_manifests=parents,physical_attempts=10,positive_physics_steps=sum(r['physics_steps'] for r in rows),active_v288_containers=owned,disk_free_gib=shutil.disk_usage(R).free/1024**3,hard_radius_m=.35,sensor_period_s=.1,physics_reruns_for_analysis=0,verification_utc_s=time.time())
(R/'evidence/final_frozen_sources01.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['source_verification','frozen_version_manifests']}))
