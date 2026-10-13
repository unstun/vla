"""Validate exact causal timeline, visible curves and the finished MP4."""
from pathlib import Path
import hashlib,json,math,os,subprocess,sys
import numpy as np
H=Path(__file__).resolve().parent;B=H.parents[1];T=Path('/data/sun/vla_mppi_20261009');O=T/'video_v140/runs/full01'
def sha(p):
 d=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024**2),b''):d.update(b)
 return d.hexdigest()
def main():
 c=json.loads((T/'video_v140/display_contract.json').read_text());s=Path(c['physical_source_root']);original=json.loads((s/'video_states.json').read_text())
 start=next(i for i,r in enumerate(original) if 'wall_monotonic_s' in r);rows=original[start:];times=np.array([r['wall_monotonic_s'] for r in rows]);n=int(np.floor((times[-1]-times[0])*30))+1
 frames=json.loads((O/'frames.json').read_text());curves=json.loads((O/'curve_frames.json').read_text());cameras=json.loads((O/'heading_camera.json').read_text())['cameras'];assert len(frames)==len(curves)==len(cameras)==n
 expected=np.maximum(0,np.searchsorted(times,times[0]+np.arange(n)/30,side='right')-1)+start
 visible=0
 for i,(f,r) in enumerate(zip(frames,curves)):
  source=original[int(expected[i])];assert f['source_state_index']==r['source_state_index']==int(expected[i])
  assert f['physics_time_s']==r['physics_time_s']==source['physics_time_s'] and r['source_wall_s']==source['wall_monotonic_s']
  assert abs(f['display_time_s']-i/30)<1e-7
  if r['trajectory_id'] is not None:
   assert r['curve_event_wall_s']<=r['source_wall_s'] and r['sampled_points']==150;visible+=1
 assert visible>n//2
 result=json.loads((O/'result.json').read_text());verification=json.loads((O/'video_verification.json').read_text());port=json.loads((O/'host_port_verification.json').read_text())
 assert result['render_only_no_physics_steps'] and port['source_unchanged'] and port['render_only_no_physics_steps'] and verification['full_decode_passed']
 assert frames[-1]['navigation_status'].startswith('arrived')
 for name,e in c['input_files'].items():assert sha(Path(name))==e,name
 master=O/'newton_stair_recorded.mp4';assert sha(master)==result['video_sha256'] and master.stat().st_size<10_000_000
 data={'passed':True,'physical_source_run':c['physical_source_run'],'physical_source_version':'v139','display_version':'v140','frames':n,'fps':30,'duration_s':n/30,'curve_visible_frames':visible,'causal_source_indices_checked':n,'no_future_curve_events':True,'terminal_frame':frames[-1]['navigation_status'],'render_only_no_physics_steps':True,'full_decode_passed':True,'video_sha256':sha(master),'video_bytes':master.stat().st_size,'video_master':str(master),'source_contract_sha256':sha(T/'video_v140/display_contract.json'),'checker_sha256':sha(Path(__file__)),'claim':'Display of the recorded successful v139 trial, including three protected replacements. No new physics or acceptance denominator.'}
 (O/'delivery_verification.json').write_text(json.dumps(data,indent=2)+'\n')
 quality={'passed':True,'display_accepted':True,'overlay_unit_tests':4,'input_source_unchanged':True,'physical_rerun':False,'physics_acceptance_from_this_render':False,'checks':{'delivery':{'path':str(O/'delivery_verification.json'),'sha256':sha(O/'delivery_verification.json')},'stream':{'path':str(O/'video_verification.json'),'sha256':sha(O/'video_verification.json')},'host':{'path':str(O/'host_port_verification.json'),'sha256':sha(O/'host_port_verification.json')}}}
 (H/'quality.json').write_text(json.dumps(quality,indent=2)+'\n');print(json.dumps(data))
if __name__=='__main__':main()
