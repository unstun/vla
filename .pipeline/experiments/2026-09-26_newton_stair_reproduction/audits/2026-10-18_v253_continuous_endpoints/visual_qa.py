from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,subprocess
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent;ROOT=HERE/'results/visual_qa';ROOT.mkdir(exist_ok=True)
video=HERE/'delivered/v255_A02_full_attempt01.mp4';times=[0,18,45,65,100,111]
def frame(t):
 p=ROOT/f'frame_{t:03d}.png'
 subprocess.run(['ffmpeg','-v','error','-ss',str(t),'-i',str(video),'-frames:v','1','-threads','1',str(p)],check=True)
 return t,p
with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(frame,times))
canvas=Image.new('RGB',(1920,768),'#101217');draw=ImageDraw.Draw(canvas);font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',17)
for i,(t,p) in enumerate(rows):
 x=(i%3)*640;y=(i//3)*384;canvas.paste(Image.open(p).resize((640,360)),(x,y+24));draw.text((x+8,y+3),f'Video t={t}s - original clocks retained',font=font,fill='white')
canvas.save(ROOT/'contact.png')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(ROOT/'manifest.json').write_text(json.dumps(dict(source_video_sha256=sha(video),samples=[dict(video_s=t,path=str(p),sha256=sha(p)) for t,p in rows],contact_sha256=sha(ROOT/'contact.png')),indent=2)+'\n')
print(ROOT/'contact.png')
