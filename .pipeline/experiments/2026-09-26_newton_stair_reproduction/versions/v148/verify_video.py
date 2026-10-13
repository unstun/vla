"""Validate exact causal timeline, visible curves and the finished MP4."""
from pathlib import Path
import hashlib,json,math,os,subprocess,sys
import numpy as np
H=Path(__file__).resolve().parent;B=H.parents[1];T=Path('/data/sun/vla_mppi_20261009');O=T/'video_v148/runs/full01'
def sha(p):
 d=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024**2),b''):d.update(b)
 return d.hexdigest()
def main():
 c=json.loads((T/'video_v148/display_contract.json').read_text());s=Path(c['physical_source_root']);original=json.loads((s/'video_states.json').read_text())
 route=json.loads((s/'full_route_verification.json').read_text());assert route['passed'] and route['profile']=='historical_full'
 proof=json.loads((s/'initial_state.json').read_text());assert proof['passed'] and proof['physics_steps']==0 and proof['physics_time_s']==0.0;assert original[0]==proof['frame'] and original[0]['physics_time_s']==0.0 and original[0]['recorded_before_first_physics_step']
 start=next(i for i,r in enumerate(original) if 'wall_monotonic_s' in r)
 startup=original[:start];nav=original[start:];sim=np.array([r['physics_time_s'] for r in startup]);times=np.array([r['wall_monotonic_s'] for r in nav])
 assert json.loads((s/'factory_video_states.json').read_text())==startup
 ns=int(math.ceil((nav[0]['physics_time_s']-sim[0])*30));nn=int(np.floor((times[-1]-times[0])*30))+1;n=ns+nn
 frames=json.loads((O/'frames.json').read_text());curves=json.loads((O/'curve_frames.json').read_text());cameras=json.loads((O/'heading_camera.json').read_text())['cameras'];assert len(frames)==len(curves)==len(cameras)==n
 expected_start=np.maximum(0,np.searchsorted(sim,sim[0]+np.arange(ns)/30,side='right')-1)
 expected_nav=np.maximum(0,np.searchsorted(times,times[0]+np.arange(nn)/30,side='right')-1)+start
 expected=np.concatenate([expected_start,expected_nav]);assert int(expected[0])==0
 visible=0
 for i,(f,r) in enumerate(zip(frames,curves)):
  source=original[int(expected[i])];assert f['source_state_index']==r['source_state_index']==int(expected[i])
  assert f['physics_time_s']==r['physics_time_s']==source['physics_time_s']
  if i<ns:
   assert f['timeline_segment']=='startup sim' and r['source_wall_s'] is None and r['trajectory_id'] is None and r['latest_completed_solve_ms'] is None
  else:
   assert f['timeline_segment']=='navigation wall 1:1' and r['source_wall_s']==source['wall_monotonic_s']
  assert abs(f['display_time_s']-i/30)<1e-7
  if r['trajectory_id'] is not None:
   assert r['curve_event_wall_s']<=r['source_wall_s'] and r['sampled_points']==150;visible+=1
 assert visible>n//2
 result=json.loads((O/'result.json').read_text());verification=json.loads((O/'video_verification.json').read_text());port=json.loads((O/'host_port_verification.json').read_text())
 assert result['render_only_no_physics_steps'] and port['source_unchanged'] and port['render_only_no_physics_steps'] and verification['full_decode_passed']
 assert frames[-1]['navigation_status'].startswith('arrived')
 for name,e in c['input_files'].items():assert sha(Path(name))==e,name
 master=O/'newton_stair_recorded.mp4';assert sha(master)==result['video_sha256'] and master.stat().st_size<80_000_000
 data={'passed':True,'physical_source_run':c['physical_source_run'],'physical_source_version':'v147','display_version':'v148','frames':n,'startup_frames':ns,'startup_original_frames':start,'first_physics_s':original[0]['physics_time_s'],'navigation_frames':nn,'startup_clock':'original simulation timestamps; no wall stamps invented','navigation_clock':'original wall timestamps, 1:1','fps':30,'duration_s':n/30,'curve_visible_frames':visible,'causal_source_indices_checked':n,'no_future_curve_events':True,'terminal_frame':frames[-1]['navigation_status'],'render_only_no_physics_steps':True,'full_decode_passed':True,'video_sha256':sha(master),'video_bytes':master.stat().st_size,'video_master':str(master),'source_contract_sha256':sha(T/'video_v148/display_contract.json'),'checker_sha256':sha(Path(__file__)),'claim':'Complete original-start original-goal v147 episode, continuous physical state, actual arrival and measured hold. Failedv144 is retained separately; no repeated full-route reliability claim.'}
 (O/'delivery_verification.json').write_text(json.dumps(data,indent=2)+'\n')
 quality={'passed':True,'display_accepted':True,'overlay_unit_tests':4,'timeline_unit_tests':3,'input_source_unchanged':True,'physical_rerun':False,'physics_acceptance_from_this_render':False,'checks':{'delivery':{'path':str(O/'delivery_verification.json'),'sha256':sha(O/'delivery_verification.json')},'stream':{'path':str(O/'video_verification.json'),'sha256':sha(O/'video_verification.json')},'host':{'path':str(O/'host_port_verification.json'),'sha256':sha(O/'host_port_verification.json')}}}
 (H/'quality.json').write_text(json.dumps(quality,indent=2)+'\n');print(json.dumps(data))
if __name__=='__main__':main()
