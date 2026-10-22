"""Side-by-side review only; hold the old failed prefix after its last frame."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;AUDITS=HERE.parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=AUDITS/'2026-10-18_v251_physical_generalization/delivered/v252_A02_full_attempt01.mp4'
new=HERE/'delivered/v255_A02_full_attempt01.mp4';out=HERE/'delivered/v252_vs_v255_A02_side_by_side.mp4'
old_quality=json.loads((AUDITS/'2026-10-18_v251_physical_generalization/results/local_quality.json').read_text())
old_entry=next(r for r in old_quality['full_video_checks'] if r['case_id']=='A02');assert sha(old)==old_entry['sha256']
from PIL import Image,ImageDraw,ImageFont
banner=HERE/'results/comparison_title.png';canvas=Image.new('RGB',(1920,34),'black');draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',19)
draw.text((12,6),'v251 / v252 A02 - FAILED prefix; final frame held',font=font,fill='white')
draw.text((972,6),'v254 / v255 A02 - single physical attempt',font=font,fill='white');canvas.save(banner)
filters="[0:v]scale=960:540,tpad=stop_mode=clone:stop_duration=900[left];[1:v]scale=960:540[right];[left][right]hstack=shortest=1,pad=1920:574:0:34:black[body];[body][2:v]overlay=0:0:shortest=1[v]"
subprocess.run(['ffmpeg','-v','error','-i',str(old),'-i',str(new),'-loop','1','-framerate','30','-i',str(banner),'-filter_complex',filters,'-map','[v]','-an','-c:v','libx264','-preset','fast','-crf','23','-threads','4','-movflags','+faststart',str(out)],check=True)
subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(out),'-f','null','-'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
(HERE/'results/comparison_video.json').write_text(json.dumps(dict(passed=True,physics_steps=0,inputs={str(old):sha(old),str(new):sha(new)},output=str(out),sha256=sha(out),bytes=out.stat().st_size,left_final_frame_held_after_prefix=True,full_decode_passed=True,claim='Recorded-state review, no additional physics. Each side begins at recorded t=0; left stays frozen after its failed recording ends.'),indent=2)+'\n')
print(out)
