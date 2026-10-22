"""Add two explicit near-stair heading controls before any route scoring."""
from pathlib import Path
import csv,hashlib,json,math,shutil
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'space_coverage_v257';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=OUT/'cases_manifest.json';d=json.loads(p.read_text());assert len(d['cases'])==50 and not (OUT/'scored').exists()
shutil.copy2(p,OUT/'construction50_manifest.json')
pool=json.loads((OUT/'discovery/candidates.json').read_text());screen={r['id']:r for r in csv.DictReader((BASE/'generic_mechanisms_v256/evaluation/spatial_screen/screen.csv').open())}
used_s={tuple(c['start']['ground']) for c in d['cases']};used_g={tuple(c['goal']['ground']) for c in d['cases']}
def pick(x,y,z,yaw,used):
 rows=[q for q in pool if screen[q['id']]['static_verdict']=='0' and abs(q['ground'][2]-z)<.08 and abs(q['yaw']-yaw)<1e-8 and tuple(q['ground']) not in used]
 q=min(rows,key=lambda q:((q['ground'][0]-x)**2+(q['ground'][1]-y)**2,q['id']));used.add(tuple(q['ground']));return dict(ground=q['ground'],yaw=yaw,construction_pose_id=q['id'],screen=screen[q['id']])
for cid,start,goal,yaw,label in [('U14',(-5.,6.8,.058),(.5,3.5,4.533),math.pi/2,'near-stair 180 degree back-facing start relative to southward flight'),('U15',(-5.,7.8,.058),(4.,.5,4.533),0.,'near-stair 90 degree transverse start')]:
 a=pick(*start,yaw,used_s);b=pick(*goal,-math.pi/2,used_g);c=dict(case_id=cid,stratum='ascent',start=a,goal=b,feature=label,expected='admit',legacy_alias=None)
 template=json.loads((OUT/'cases/A04/scenario.json').read_text());template.update(case_id=cid,spawn_ground_xyz_m=a['ground'],spawn_yaw_rad=a['yaw'],goal_ground_xyz_m=b['ground'],goal_yaw_rad=b['yaw'])
 f=OUT/'cases'/cid;f.mkdir();(f/'scenario.json').write_text(json.dumps(template,indent=2)+'\n');(f/'endpoints.txt').write_text(' '.join(map(str,a['ground'][:2]+[a['ground'][2]+.3]+b['ground'][:2]+[b['ground'][2]+.3,a['yaw'],b['yaw']]))+'\n');c.update(scenario_sha256=sha(f/'scenario.json'),endpoints_sha256=sha(f/'endpoints.txt'));d['cases'].append(c)
for c in d['cases']:
 if c['case_id'] in ('U06','U11'):c['feature']='far approach facing north; actual departure-heading difference reported after planning'
d.update(distinct_tuples=52,distinct_spatial_pairs=52,unique_start_positions=52,unique_goal_positions=52,construction50_manifest_sha256=sha(OUT/'construction50_manifest.json'),pre_score_expansion='Two additional distinct near-stair heading controls ensure explicit 180/90 degree inputs at the actual stair entrance. Original fifty cases/fixtures preserved; no route call used.')
keys=[tuple(c['start']['ground']+[c['start']['yaw']]+c['goal']['ground']+[c['goal']['yaw']]) for c in d['cases']];assert len(set(keys))==52
assert len({tuple(c['start']['ground']) for c in d['cases']})==len({tuple(c['goal']['ground']) for c in d['cases']})==52
p.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(dict(cases=len(d['cases']),added=['U14','U15'],before_scoring=True)))
