"""Decode every returned regular MP4 locally, without rendering new frames."""
from pathlib import Path
import subprocess,hashlib,json,concurrent.futures,time
H=Path(__file__).resolve().parent
videos=sorted((H/'delivered').glob('v289_*_full_attempt01.mp4'));assert len(videos)==10
inventory=json.loads((H/'physical_return/return_inventory.json').read_text())['videos']
def check(p):
 assert p.is_file() and not p.is_symlink()
 sha=hashlib.sha256(p.read_bytes()).hexdigest();assert sha==inventory[p.name]['sha256']
 t=time.monotonic();cmd=['ffmpeg','-v','error','-threads','2','-i',str(p),'-f','null','-']
 r=subprocess.run(cmd,capture_output=True,text=True)
 return dict(file=p.name,sha256=sha,returncode=r.returncode,full_local_decode_passed=r.returncode==0 and not r.stderr.strip(),stderr=r.stderr,wall_s=time.monotonic()-t)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(check,videos))
result=dict(passed=all(r['full_local_decode_passed'] for r in rows),files=rows,physics_steps=0,rendering_steps=0)
(H/'evidence/local_full_video_decode01.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed'];print('All ten regular MP4s fully decoded locally')
