"""Hash derivative deliverables and retain small visual-review frames; no physics."""
from pathlib import Path
import hashlib,json,shutil,subprocess
HERE=Path(__file__).resolve().parent
REMOTE=Path('/data/sun/vla_mppi_20261009');TASK=REMOTE/'trials/v231_linux_full_attempt01'
OUT=HERE/'results';DISPLAY=TASK/'video_v231/runs/full01';DELIVERED=HERE/'delivered'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for data in iter(lambda:f.read(4*1024**2),b''):h.update(data)
 return h.hexdigest()
for name in ('delivery_verification.json','video_verification.json','host_port_verification.json','display_contract.json'):
 shutil.copyfile(DISPLAY/name,OUT/name)
for name in ('v231_display_tests01.log','v231_body_margin01.log','v231_closeout01.log','v231_render01.log','v231_postprocess01.log','v231_diagnostic_metrics01.log','v231_compare_video01.log','v231_compare_video02.log'):
 shutil.copyfile(REMOTE/name,OUT/name)
samples=OUT/'visual_review';samples.mkdir(exist_ok=True)
for physical_s,index in ((45,0),(48,90),(55,300)):
 subprocess.run(['ffmpeg','-v','error','-i',str(DELIVERED/'stairs_physics_45_55.mp4'),'-vf',f'select=eq(n\\,{index})','-vsync','0','-frames:v','1',str(samples/f'physics_{physical_s}s.png')],check=True)
tracked=[p for p in DISPLAY.rglob('*') if p.is_file() and ('frame_samples' not in p.parts)]
proof={'claim':'Derivative videos only; physical gate failed. Display validation is independent of physical acceptance.',
 'videos':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size,'remote_path':str(p)} for p in DELIVERED.glob('*.mp4')},
 'remote_display_artifacts':{str(p):{'sha256':sha(p),'bytes':p.stat().st_size} for p in tracked},
 'analysis_tools':{p.name:sha(p) for p in HERE.glob('*') if p.is_file() and p.suffix in ('.py','.cpp','.txt','.json')},
 'local_return_policy':'Only derivative review videos, compact result/verification receipts and three PNGs; no raw zip/NPZ/telemetry/build cache.'}
(OUT/'delivery_manifest.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof['videos'],indent=2))
