"""Freeze fifty spatially distinct cases from geometry only, before route scoring."""
from pathlib import Path
import csv,hashlib,json,math
BASE=Path('/data/sun/vla_mppi_20261009');HERE=Path(__file__).resolve().parent;EXP=HERE.parents[1]
OUT=BASE/'space_coverage_v257';D=OUT/'discovery';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pool=json.loads((D/'candidates.json').read_text());screen={r['id']:r for r in csv.DictReader((BASE/'generic_mechanisms_v256/evaluation/spatial_screen/screen.csv').open())}
legal=[dict(p,screen=screen[p['id']]) for p in pool if screen[p['id']]['static_verdict']=='0']
used_start=set();used_goal=set();cases=[]
def xyzkey(p):return tuple(round(v,6) for v in p['ground'])
def pick(anchor,yaw,used,region=None,boundary=False):
 x,y,z=anchor
 rows=[p for p in legal if abs(p['ground'][2]-z)<.08 and abs(math.remainder(p['yaw']-yaw,2*math.pi))<1e-7 and xyzkey(p) not in used]
 if region:rows=[p for p in rows if region(p['ground'])]
 if boundary:rows=[p for p in rows if min(float(p['screen']['edge_margin']),float(p['screen']['exact_solid_margin']))<.08]
 assert rows,(anchor,yaw)
 p=min(rows,key=lambda p:((p['ground'][0]-x)**2+(p['ground'][1]-y)**2,p['id']))
 used.add(xyzkey(p));return dict(ground=p['ground'],yaw=yaw,construction_pose_id=p['id'],screen=p['screen'])
def exact(p):
 return dict(ground=p['ground'],yaw=p['yaw'],source='unchanged original v242 endpoint')
def add(cid,stratum,a,b,feature,expected='admit',alias=None):
 cases.append(dict(case_id=cid,stratum=stratum,start=a,goal=b,feature=feature,expected=expected,legacy_alias=alias))
old=json.loads((HERE.parent/'v242/cases_manifest.json').read_text())['cases'];old={c['case_id']:c for c in old}
# Exactly preserve the two explicitly requested historical hard routes.
for cid in ('A04','G05'):
 c=old[cid];a=exact(c['start']);b=exact(c['goal']);used_start.add(xyzkey(a));used_goal.add(xyzkey(b));add(cid,'ascent',a,b,'original narrow corridor turn' if cid=='A04' else 'original low-margin upper destination',alias=cid)
# Spread starts across the accessible outer approach, and goals over the upper hall/wings.
up_starts=[(-6.4,6.8),(-5.5,7.4),(-4.5,7.2),(-3.5,8.0),(-1.5,7.4),(.5,7.5),(2.5,7.3),(4.5,7.6),(6.5,7.5),(8.8,7.0),(9.6,3.0),(9.6,-2.5),(6.0,-8.2)]
up_goals=[(5,4),(6,5),(-4,-3.5),(-3,3.7),(1,4),(3,2),(-4,1),(0,-4),(4,-3),(7,-5.5),(8,-6.5),(8,7),(-2,-2)]
headings=[-math.pi/2,-math.pi/4,-3*math.pi/4,0.,math.pi,math.pi/2,-math.pi/2,0.,math.pi,-math.pi/4,math.pi/2,-math.pi/2,math.pi]
for k,(s,g,yaw) in enumerate(zip(up_starts,up_goals,headings),1):
 a=pick((*s,.058),yaw,used_start);b=pick((*g,4.533),[-math.pi/2,0.,math.pi/2,math.pi][k%4],used_goal)
 add(f'U{k:02d}','ascent',a,b,'180 degree back-facing start' if yaw==math.pi/2 else 'diverse staircase approach and upper destination')
down_s=[(6.3,4.5),(-1,2.5),(-4.5,-3.5),(-4,4.5),(-3,-1),(0,0),(2,3),(4,-3),(0,-4),(4,4),(8,7),(8,-7),(6,-4),(-4,1),(2,-1)]
down_g=[(-5.5,7.2),(-3,7.5),(1,7.6),(-6.3,8),(-4.5,8),(3.5,8),(5.5,7),(7,7.5),(9.5,5),(9.5,0),(9.5,-5),(4.5,-8.1),(-1,-8.1),(-6.5,-7),(-6.7,-2)]
for k,(s,g) in enumerate(zip(down_s,down_g),1):
 a=pick((*s,4.533),[0,math.pi/4,math.pi/2,math.pi,-math.pi/2,-math.pi/4,-3*math.pi/4,3*math.pi/4][k%8],used_start)
 b=pick((*g,.058),[-math.pi/2,0,math.pi/2,math.pi][k%4],used_goal)
 add(f'D{k:02d}','descent',a,b,'reverse cross-floor from a distinct upper region')
# Actual intermediate physical floors and staircase corner regions, not slice aliases.
mid=[((-4,-4,1.558),(4,3,4.533)),((7.8,6.4,3.058),(-2,3,4.533)),((6.5,-5.9,3.058),(0,7.4,.058)),((0,-4.3,1.558),(7,7.5,.058)),
     ((-5.7,7.5,.058),(-3,-4.2,1.558)),((8,7,4.533),(7.5,6.4,3.058)),((-2,2,4.533),(8,-6.0,3.058)),((2,7.5,.058),(3,-4.3,1.558))]
for k,(s,g) in enumerate(mid,1):
 a=pick(s,[0.,math.pi/2,math.pi,-math.pi/2][k%4],used_start);b=pick(g,[math.pi/2,0.,-math.pi/2,math.pi][k%4],used_goal)
 add(f'M{k:02d}','intermediate',a,b,'intermediate landing start' if k<=4 else 'intermediate landing goal')
same=[((-6,7.4,.058),(-4,8,.058)),((2,8,.058),(7.5,7,.058)),((9.5,4,.058),(8,-8,.058)),((4,5,4.533),(8,7.5,4.533)),((4,-4.5,4.533),(8,-7,4.533)),((-4,4,4.533),(-4,-4,4.533))]
for k,(s,g) in enumerate(same,1):
 a=pick(s,[math.pi,0.,-math.pi/2,math.pi/2][k%4],used_start);b=pick(g,[0.,math.pi/2,math.pi,-math.pi/2][k%4],used_goal)
 add(f'S{k:02d}','same_floor',a,b,'actual pillar/wing opening/corridor corner; source has open halls rather than separate rooms')
# Near-boundary legal cases use geometry clearance, never route success, as selection.
for k,(s,g,z) in enumerate([((-6,7.5),(-5.9,6.7),.058),((2,3),(-5.8,4.8),4.533),((4,-4),(5.8,-5.2),4.533)],1):
 a=pick((*s,z),0.,used_start);b=pick((*g,z),math.pi/2,used_goal,boundary=True)
 add(f'E{k:02d}','boundary',a,b,'low positive physical margin legal boundary')
# Original B08 is retained verbatim as an expected solid collision, not repaired.
c=old['B08'];a=exact(c['start']);b=exact(c['goal']);b['yaw']=0.;used_start.add(xyzkey(a));used_goal.add(xyzkey(b));add('E04','boundary',a,b,'original B08 solid-intruding destination','reject','B08')
# Other dead-corner controls are selected by an existing typed hard violation.
for k,(anchor,z,kind) in enumerate([((-7.1,5.8),.058,'wall'),((9.5,-3.2),4.533,'edge')],5):
 bad=[p for p in pool if abs(p['ground'][2]-z)<.08 and screen[p['id']]['static_verdict']!='0' and xyzkey(p) not in used_goal]
 assert bad
 p=min(bad,key=lambda p:(p['ground'][0]-anchor[0])**2+(p['ground'][1]-anchor[1])**2)
 b=dict(ground=p['ground'],yaw=p['yaw'],construction_pose_id=p['id'],screen=screen[p['id']]);used_goal.add(xyzkey(b))
 a=pick((0,7.5,.058) if z<1 else (4,0,4.533),0.,used_start)
 add(f'E{k:02d}','boundary',a,b,'predeclared illegal '+kind+' dead corner','reject')
assert len(cases)==50
keys=[tuple(c['start']['ground']+[c['start']['yaw']]+c['goal']['ground']+[c['goal']['yaw']]) for c in cases]
spatial=[tuple(c['start']['ground']+c['goal']['ground']) for c in cases]
assert len(set(keys))==len(set(spatial))==50
# Every requested heading is explicit; no terminal tangent inference.
template=json.loads((EXP/'inputs/historical_full_building.json').read_text())
for c in cases:
 scenario=dict(template);scenario.update(case_id=c['case_id'],route_profile='generalization',spawn_ground_xyz_m=c['start']['ground'],spawn_yaw_rad=c['start']['yaw'],goal_ground_xyz_m=c['goal']['ground'],goal_yaw_rad=c['goal']['yaw'],profile_source='v257 pre-score spatial construction; no route result used',scene_condition='Complete original Building; no actor')
 for key in ('native_support_screen','initial_center_distance_m','initial_placement_pass'):scenario.pop(key,None)
 f=OUT/'cases'/c['case_id'];f.mkdir(parents=True,exist_ok=False);p=f/'scenario.json';p.write_text(json.dumps(scenario,indent=2)+'\n')
 (f/'endpoints.txt').write_text(' '.join(map(str,c['start']['ground'][:2]+[c['start']['ground'][2]+.3]+c['goal']['ground'][:2]+[c['goal']['ground'][2]+.3,c['start']['yaw'],c['goal']['yaw']]))+'\n')
 c.update(scenario_sha256=sha(p),endpoints_sha256=sha(f/'endpoints.txt'))
manifest=dict(version='v257',frozen_before_route_scoring=True,calls_per_case=1,cases=cases,distinct_tuples=len(set(keys)),distinct_spatial_pairs=len(set(spatial)),unique_start_positions=len({tuple(c['start']['ground']) for c in cases}),unique_goal_positions=len({tuple(c['goal']['ground']) for c in cases}),construction='native support plus exact raw solid endpoint geometry only; no route scores or post-score case substitution',discovery={str(p.relative_to(OUT)):sha(p) for p in D.rglob('*') if p.is_file()},rl_sha256='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b',hard_radius_m=.35,sensor_period_s=.1,source_geometry_limit='Original Building has open halls/wing openings and pillars; do not label absent separate rooms or conventional door leaves as tested.',prospective_gate=dict(legal_full_chain_rate_min=.9,first_gpmp_among_global_min=.9,illegal_admissions_max=0,admitted_negative_raw_margin_max=0,physical_representatives=10),selection='3 ascent including A04/G05 and backward start; 2 descent; 2 intermediate including start and goal; 2 same-floor constrictions; 1 legal boundary. Rank eligible remaining cases by minimum edge/solid margin, then greatest initial heading turn.')
(OUT/'cases_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({k:v for k,v in manifest.items() if k not in ('cases','discovery')},indent=2))
