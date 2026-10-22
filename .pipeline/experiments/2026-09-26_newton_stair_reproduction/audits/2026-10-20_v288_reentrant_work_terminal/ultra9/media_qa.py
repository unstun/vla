"""Local verification of the ten returned regular review videos."""
from pathlib import Path
import json,subprocess,hashlib
from PIL import Image,ImageDraw,ImageFont
H=Path(__file__).resolve().parent

def main():
 cases=json.loads((H.parents[2]/'versions/v288/cases_manifest.json').read_text())['physical_cases']
 out=H/'visual_review';out.mkdir(exist_ok=True);rows=[];tiles=[]
 font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',18)
 for case in cases:
  p=H/'delivered'/f'v288_{case}_full_attempt01.mp4';assert p.is_file() and not p.is_symlink()
  data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]));s=next(v for v in data['streams'] if v['codec_type']=='video');duration=float(data['format']['duration'])
  assert s['width']==1280 and s['height']==720 and s['avg_frame_rate']=='30/1'
  row=dict(case_id=case,video=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size,width=s['width'],height=s['height'],fps=s['avg_frame_rate'],duration_s=duration,frames=int(s['nb_frames']),samples=[])
  for i,ratio in enumerate([.2,.85]):
   target=out/f'{case}_{i+1}.png';t=duration*ratio
   subprocess.run(['ffmpeg','-nostdin','-v','error','-ss',str(t),'-i',str(p),'-frames:v','1','-y',str(target)],check=True)
   row['samples'].append(dict(time_s=t,file=str(target.resolve())))
   tile=Image.new('RGB',(640,390),'#111722');tile.paste(Image.open(target).convert('RGB').resize((640,360)),(0,30));ImageDraw.Draw(tile).text((8,5),f'{case}  t={t:.2f}s  v288',font=font,fill='white');tiles.append(tile)
  rows.append(row)
 for page in range(2):
  sheet=Image.new('RGB',(1280,1950),'black')
  for i,tile in enumerate(tiles[page*10:(page+1)*10]):sheet.paste(tile,((i%2)*640,(i//2)*390))
  sheet.save(out/f'contact_sheet_{page+1}.png')
 (H/'evidence/local_media_verification01.json').write_text(json.dumps(dict(regular_files=10,visual_samples=20,visual_review_pending=True,cases=rows),indent=2)+'\n')
 print('Ten regular1280x720/30fps files verified;20 source frames ready for visual review')
if __name__=='__main__':main()
