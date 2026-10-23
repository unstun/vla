"""Measured zero-command episodes; unavailable/censored drift is never zero success."""
import math

def summarize(rows,goal,nav_start):
 if not rows:return {'terminal_seen':False,'episodes':[],'first':None,'reason':'no telemetry'}
 times=[r['physics_time_s'] for r in rows];assert all(b>a for a,b in zip(times,times[1:]))
 position=lambda r:r['body_sensor']['position']
 zero=lambda r:max(map(abs,r['effective_command']))<1e-9
 entered=next((i for i,r in enumerate(rows) if r['physics_time_s']>=nav_start and math.dist(position(r)[:2],goal[:2])<=.25 and abs(position(r)[2]-goal[2]-.3)<=.2),None)
 if entered is None:return {'terminal_seen':False,'episodes':[],'first':None,'reason':'did not enter original terminal region'}
 episodes=[];i=entered
 while i<len(rows):
  if not zero(rows[i]):i+=1;continue
  start=i;j=i+1
  while j<len(rows) and zero(rows[j]):j+=1
  band=rows[start:j];anchor=position(band[0]);dist=lambda r:math.dist(position(r)[:2],anchor[:2])*100
  pd=next((r for r in band if r['stance_mode']=='STAND_TRANSITION'),None)
  fixed=next((r for r in band if r['stance_mode']=='FIXED_STAND'),None)
  pdtime=pd['physics_time_s'] if pd else None
  episodes.append({'start_s':band[0]['physics_time_s'],'end_s':band[-1]['physics_time_s'],
    'start_telemetry_row':start+1,'end_telemetry_row':j,'samples':len(band),
    'max_displacement_cm':max(map(dist,band)),'net_displacement_cm':dist(band[-1]),
    'max_pre_pd_displacement_cm':max(dist(r) for r in band if pdtime is None or r['physics_time_s']<=pdtime),
    'pd_entry_s':pdtime,'pd_delay_s':None if pd is None else pdtime-band[0]['physics_time_s'],
    'fixed_stand_s':None if fixed is None else fixed['physics_time_s'],
    'command_restarted':j<len(rows),'pd_entry_censored':pd is None,
    'candidate_assisted_samples':sum(bool(any(r.get('settling_contact_mask',[]))) and r['stance_mode']=='STAND_SETTLING' for r in band),
    'plot':[{'t':r['physics_time_s'],'cm':dist(r),'mode':r['stance_mode']} for k,r in enumerate(band) if k%5==0 or k==len(band)-1]})
  i=j
 return {'terminal_seen':True,'terminal_entry_s':rows[entered]['physics_time_s'],'episodes':episodes,
         'first':episodes[0] if episodes else None,'worst_episode_cm':max((e['max_displacement_cm'] for e in episodes),default=None),
         'restart_count':sum(e['command_restarted'] for e in episodes)}
