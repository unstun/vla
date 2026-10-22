"""Return only compact proof and review videos; retain raw capture/builds remotely."""
from pathlib import Path
import hashlib,json,shutil,time
HERE=Path(__file__).resolve().parent;EXP=HERE.parents[1];BASE=Path('/data/sun/vla_mppi_20261009')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();entries={};retained={}
def bind(p):entries[str(p.relative_to(HERE))]=dict(sha256=sha(p),bytes=p.stat().st_size,remote_path=str(p))
def copy(p,rel):
 q=HERE/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);bind(q)
for version in ('v253','v254'):
 root=BASE/('generic_mechanisms_'+version)/'evaluation'
 for n in ('matrix_summary.json','matrix_table.csv','offline_gate.json','selection.json','linked_libraries.txt'):
  if (root/n).is_file():copy(root/n,Path('offline')/version/n)
 for group in ('measured_start','measured_fixture','historical02','support'):
  for p in (root/group).glob('*'):
   if p.is_file() and p.suffix in ('.json','.log','.txt') and p.stat().st_size<2_000_000:copy(p,Path('offline')/version/group/p.name)
 for p in (root/'scored').glob('*/rep*/summary.json'):copy(p,Path('offline')/version/'scored'/p.relative_to(root/'scored'))
 for p in root.rglob('route.csv'):retained[str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size,regenerate='Frozen versions/'+version+'/run_matrix.py with the recorded case fixture')
root=HERE/'physical/A02'
for p in (root/'results').rglob('*'):
 if p.is_file() and p.suffix in ('.json','.csv','.log','.yaml'):
  if p.stat().st_size<2_000_000:bind(p)
  else:retained[str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size)
for p in root.glob('*.py'):bind(p)
for p in root.glob('*.json'):bind(p)
for p in (BASE/'generalization_v255').rglob('*.json'):
 if p.stat().st_size<2_000_000:copy(p,Path('preflight_and_execution')/p.relative_to(BASE/'generalization_v255'))
for p in (BASE/'generalization_v255/raw_pose_audit01').glob('*.csv'):copy(p,Path('results/raw_pose_audit01')/p.name)
if (BASE/'generalization_v255/raw_pose_audit01/summary.json').exists():copy(BASE/'generalization_v255/raw_pose_audit01/summary.json','results/raw_pose_audit01/summary.json')
raw=BASE/'trials/v255_A02_attempt01/runs/v255_A02_attempt01/raw_capture.zip'
if raw.exists():retained[str(raw)]=dict(sha256=sha(raw),bytes=raw.stat().st_size,regenerate='Run v255 launch once in a fresh explicitly authorized attempt; original raw archive is the sole run source')
render=BASE/'trials/v255_A02_attempt01'/('video_v255_render'+__import__('os').environ.get('V255_RENDER_ID','01'))
for rel in ('display_contract.json','runs/full01/result.json','runs/full01/display_validation.json','runs/full01/video_verification.json','runs/full01/delivery_verification.json','runs/full01/host_port_verification.json','runs/full01/quality.json'):
 p=render/rel
 if p.exists():copy(p,Path('physical/A02/results/display')/p.name)
for p in (HERE/'delivered').glob('*.mp4'):bind(p)
for p in BASE.glob('v25[345]_*.log'):
 if p.stat().st_size<2_000_000:copy(p,Path('results/logs')/p.name)
for p in (HERE/'results').glob('*.json'):bind(p)
(HERE/'return_manifest.json').write_text(json.dumps(dict(host='gpu5070ti',verified_utc_s=time.time(),entries=entries,retained_remote=retained,return_files=len(entries),return_bytes=sum(v['bytes'] for v in entries.values()),claim='Compact evidence and full review MP4 only; raw clouds/states/build intermediates remain remote'),indent=2)+'\n')
print(json.dumps(dict(return_files=len(entries),return_bytes=sum(v['bytes'] for v in entries.values()))),flush=True)
