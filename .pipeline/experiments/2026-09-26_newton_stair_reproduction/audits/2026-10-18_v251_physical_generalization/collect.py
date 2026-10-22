"""Explicit compact return list; raw archives, arrays and builds stay remote."""
from pathlib import Path
import hashlib,json,shutil,time
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();entries={};retained={}
final=json.loads((HERE/'results/render_status03.json').read_text())
assert len(final)==3 and all(r['exit_code']==0 and r['physics_steps']==0 for r in final)
def bind(p):
 entries[str(p.relative_to(HERE))]=dict(sha256=sha(p),bytes=p.stat().st_size,remote_path=str(p))
def copy(p,relative):
 q=HERE/relative;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);bind(q)
for cid in ('A02','G07','R11'):
 root=HERE/'physical'/cid
 for p in (root/'results').rglob('*'):
  if p.is_file() and p.suffix in ('.json','.csv','.log','.yaml'):
   if p.stat().st_size>2_000_000:
    retained[str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size);continue
   bind(p)
 for p in root.glob('*.py'):bind(p)
 for p in root.glob('*.json'):bind(p)
 for p in root.glob('render_attempt*_source/*.py'):bind(p)
 for p in root.glob('render_attempt*_source/*.json'):bind(p)
 raw=BASE/'trials'/f'v252_{cid}_attempt01'/'runs'/f'v252_{cid}_attempt01'
 archive=raw/'raw_capture.zip';retained[str(archive)]=dict(sha256=sha(archive),bytes=archive.stat().st_size)
 render=BASE/'trials'/f'v252_{cid}_attempt01'/'video_v252_render03'
 for relative in ('display_contract.json','runs/full01/result.json','runs/full01/display_validation.json','runs/full01/video_verification.json','runs/full01/delivery_verification.json','runs/full01/host_port_verification.json','runs/full01/quality.json'):
  p=render/relative
  if p.exists():copy(p,Path('physical')/cid/'results/display'/p.name)
 proof=BASE/'generalization_v252'/cid
 for p in proof.rglob('*.json'):copy(p,Path('preflight_and_execution')/cid/p.relative_to(proof))
 video=HERE/'delivered'/f'v252_{cid}_full_attempt01.mp4';assert video.is_file();bind(video)
for tag in ('measured_start01','measured_start02','raw_pose_audit01'):
 for p in (BASE/'generalization_v252'/tag).glob('*'):
  if p.is_file() and p.suffix in ('.csv','.json','.txt','.log'):copy(p,Path('results')/tag/p.name)
for p in BASE.glob('v252_*.log'):
 if p.is_file() and p.stat().st_size<2_000_000:copy(p,Path('results/logs')/p.name)
for p in (HERE/'results').glob('*.json'):bind(p)
receipt=dict(host='gpu5070ti',verified_epoch_s=time.time(),entries=entries,retained_remote=retained,
 return_files=len(entries),return_bytes=sum(r['bytes'] for r in entries.values()),
 claim='Full review MP4s and compact reports only; no raw cloud/state archive or build cache downloaded')
(HERE/'return_manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(return_files=receipt['return_files'],return_bytes=receipt['return_bytes'])),flush=True)
