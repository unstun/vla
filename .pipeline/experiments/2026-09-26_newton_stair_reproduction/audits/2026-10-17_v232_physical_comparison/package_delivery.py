"""Hash bounded review artifacts and extract physical-time visual checks; no physics."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
ROOT=Path('/data/sun/vla_mppi_20261009/trials/v233_linux_full_attempt01/video_v233')
OUT=HERE/'results';review=OUT/'visual_review';review.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in ('display_contract.json','restored_text_inputs.json'):
 p=ROOT/name
 if p.is_file():(OUT/name).write_bytes(p.read_bytes())
for name in ('video_verification.json','host_port_verification.json','display_verification.json'):
 p=ROOT/'runs/full01'/name
 if p.is_file():(OUT/name).write_bytes(p.read_bytes())
checks={}
for p in sorted((HERE/'delivered').glob('*.mp4')):
 subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','null','-'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 stream=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,nb_read_frames,avg_frame_rate:format=duration','-of','json',str(p)],text=True))
 checks[p.name]=dict(sha256=sha(p),bytes=p.stat().st_size,full_decode_passed=True,probe=stream)
for t in (45,48,55):
 video=HERE/'delivered/full_physics_comparison.mp4';target=review/f'physics_{t}s.png'
 subprocess.run(['ffmpeg','-v','error','-ss',str(t),'-i',str(video),'-frames:v','1',str(target)],check=True)
files={str(p.relative_to(HERE)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in HERE.rglob('*') if p.is_file() and 'work' not in p.relative_to(HERE).parts and p.name!='delivery_manifest.json'}
(OUT/'delivery_manifest.json').write_text(json.dumps(dict(passed=True,physics_attempts=1,video_checks=checks,files=files,excluded='remote work, raw archive, build cache and renderer capture'),indent=2)+'\n')
print(json.dumps(checks,indent=2))
