"""Preserve recorded startup states and the original navigation wall timeline."""
from pathlib import Path
import json,math
import numpy as np

def load_rows(source):
 original=json.loads((Path(source)/'video_states.json').read_text())
 if original[0].get('physics_time_s')!=0.0 or original[0].get('physics_steps')!=0 or not original[0].get('recorded_before_first_physics_step'):raise ValueError('Expected real zero-time initial frame')
 first=next(i for i,r in enumerate(original) if 'wall_monotonic_s' in r)
 if first==0:raise ValueError('Expected original recorded startup segment')
 startup=original[:first];navigation=original[first:]
 if any('wall_monotonic_s' in r for r in startup):raise ValueError('Unexpected mixed startup clocks')
 sim=np.array([r['physics_time_s'] for r in startup]);times=np.array([r['wall_monotonic_s'] for r in navigation])
 if not np.isfinite(sim).all() or not np.isfinite(times).all() or np.any(np.diff(sim)<=0) or np.any(np.diff(times)<=0):raise ValueError('Invalid recorded clock sequence')
 n=int(math.ceil((navigation[0]['physics_time_s']-sim[0])*30))
 if n<=0:raise ValueError('Invalid startup/navigation transition')
 grid=sim[0]+np.arange(n)/30;ids=np.maximum(0,np.searchsorted(sim,grid,side='right')-1)
 rows=[dict(startup[int(k)],source_state_index=int(k),display_time_s=i/30,timeline_segment='startup sim') for i,k in enumerate(ids)]
 wall=times[0]+np.arange(int(np.ceil((times[-1]-times[0])*30))+1)/30
 ids=np.maximum(0,np.searchsorted(times,wall,side='right')-1)
 rows.extend(dict(navigation[int(k)],source_state_index=first+int(k),display_time_s=(n+i)/30,timeline_segment='navigation wall 1:1') for i,k in enumerate(ids))
 return rows
