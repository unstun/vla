"""Physical-time-aligned comparison, FFmpeg pipes replacing unavailable imageio; no state interpolation."""
from pathlib import Path
import hashlib,json,math,os,subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont
class Reader:
 def __init__(self,path):
  stream=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','json',str(path)],text=True))['streams'][0]
  self.width,self.height=stream['width'],stream['height']
  self.process=subprocess.Popen(['ffmpeg','-v','error','-i',str(path),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE)
 def get_next_data(self):
  data=self.process.stdout.read(self.width*self.height*3)
  if len(data)!=self.width*self.height*3:raise RuntimeError('Unexpected decoded video end')
  return np.frombuffer(data,dtype=np.uint8).reshape(self.height,self.width,3)
 def close(self):
  if self.process.poll() is None:self.process.terminate()
  self.process.stdout.close();self.process.wait()
class Writer:
 def __init__(self,path,fps):self.path,self.fps,self.process=path,fps,None
 def append_data(self,array):
  if self.process is None:
   height,width,_=array.shape
   self.process=subprocess.Popen(['ffmpeg','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',str(width)+'x'+str(height),'-framerate',str(self.fps),'-i','pipe:0','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(self.path)],stdin=subprocess.PIPE)
  self.process.stdin.write(array.tobytes())
 def close(self):
  if self.process is not None:
   self.process.stdin.close()
   if self.process.wait()!=0:raise RuntimeError('Comparison encoding failed')

HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
ROOT=Path('/data/sun/vla_mppi_20261009/trials')
SOURCES=[ROOT/'v219_linux_full_attempt01/video_v220/runs/full01',ROOT/'v231_linux_full_attempt01/video_v231/runs/full01']
TITLES=['v219 reference','v230 navigation / v231 physics']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 delivered=HERE/'delivered';delivered.mkdir(exist_ok=True)
 sources=[]
 for root in SOURCES:
  frames=json.loads((root/'frames.json').read_text());times=np.array([f['physics_time_s'] for f in frames]);assert np.all(np.diff(times)>=0)
  path=root/'newton_stair_recorded.mp4';sources.append({'root':root,'frames':frames,'times':times,'path':path})
 font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
 for name,begin,end,scale in [('full_physics_comparison',0.,max(s['times'][-1] for s in sources),.5),('stairs_physics_45_55',45.,55.,1.)]:
  width,height=int(1280*scale),int(720*scale);header=44;fps=30;count=int(math.ceil((end-begin)*fps))+1
  readers=[Reader(s['path']) for s in sources]
  indexes=[-1,-1];images=[None,None];mapping=[];out=delivered/(name+'.mp4')
  writer=Writer(out,fps)
  try:
   for i in range(count):
    t=begin+i/fps;canvas=Image.new('RGB',(2*width,height+header),(12,18,25));draw=ImageDraw.Draw(canvas);record={'physics_grid_s':t,'sources':[]}
    for side,(reader,source) in enumerate(zip(readers,sources)):
     ended=t>float(source['times'][-1])+1e-6
     if ended:
      draw.text((side*width+20,header+height//2),f"Recording ended at {source['times'][-1]:.3f}s",font=font,fill=(235,190,120));record['sources'].append({'ended':True,'last_physics_s':float(source['times'][-1])})
     else:
      index=int(max(0,np.searchsorted(source['times'],t+1e-9,side='right')-1))
      while indexes[side]<index:images[side]=reader.get_next_data();indexes[side]+=1
      image=Image.fromarray(images[side]);image=image.resize((width,height),Image.Resampling.LANCZOS) if scale!=1 else image
      canvas.paste(image,(side*width,header));record['sources'].append({'frame':index,'source_state_index':source['frames'][index]['source_state_index'],'actual_physics_s':float(source['times'][index])})
     draw.text((side*width+12,10),f'{TITLES[side]} | physics {t:.2f}s',font=font,fill=(245,245,245))
    writer.append_data(np.asarray(canvas));mapping.append(record)
  finally:
   writer.close()
   for reader in readers:reader.close()
  subprocess.run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,nb_read_frames,avg_frame_rate','-of','json',str(out)],text=True))['streams'][0]
  assert int(probe['nb_read_frames'])==count and probe['avg_frame_rate']=='30/1'
  proof={'passed':True,'video_sha256':sha(out),'video_bytes':out.stat().st_size,'frames':count,'begin_physics_s':begin,'end_physics_s':end,
   'source_videos':{str(s['path']):sha(s['path']) for s in sources},'source_frame_manifests':{str(s['root']/'frames.json'):sha(s['root']/'frames.json') for s in sources},
   'selection':'latest recorded video frame not later than common physical time; black after a recording ends; no interpolation','stream':probe,'frame_mapping':mapping}
  (HERE/'results'/(name+'_verification.json')).write_text(json.dumps(proof,indent=2)+'\n');print(name,probe,out.stat().st_size,flush=True)
if __name__=='__main__':main()
