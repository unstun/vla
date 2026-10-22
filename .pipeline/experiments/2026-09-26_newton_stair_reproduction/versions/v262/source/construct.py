"""Pre-score requests and original-mesh path witnesses from a certified graph.

Selecting NEW benchmark poses from geometry is construction, not snapping a
runtime request. Mandatory historical requests keep their exact original poses.
No native PCT score is read here.
"""
from pathlib import Path
import hashlib, json, math, os, pickle, sys
os.environ['OPENBLAS_NUM_THREADS']='1'; os.environ['OMP_NUM_THREADS']='1'
import numpy as np

HERE=Path(__file__).resolve().parent; EXP=HERE.parents[1]
AUDIT=EXP/'audits/2026-10-18_v259_equivalent_geometry_repairs'
sys.path.insert(0,str(AUDIT))
from mesh_route_certificate import MeshRouteCertificate
BASE=Path('/data/sun/vla_mppi_20261009'); OUT=BASE/'mesh_benchmark_v262'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (OUT/'cases_manifest.json').exists()
tri=BASE/'support_coverage_v134/triangles.f64'
receipt=json.loads((OUT/'component_receipt.json').read_text())
assert sha(tri)==receipt['original_triangles_sha256']
mesh=MeshRouteCertificate(np.fromfile(tri,dtype='<f8').reshape(-1,3,3))
with (OUT/'mesh_component.pkl').open('rb') as f: cache=pickle.load(f)
parent=cache['parent'];mesh.states=cache['states'];mesh.edges=cache['edges']
assert mesh.cells==cache['cells']
poses=json.loads((OUT/'reachable_poses.json').read_text())
old={c['case_id']:c for c in json.loads((HERE.parent/'v257/cases_manifest.json').read_text())['cases']}
root=receipt['root']; used_start=set(); used_goal=set(); cases=[]; proposals=[]
xyz=lambda p:tuple(round(v,8) for v in p['ground'])
def original(cid,which):
    p=old[cid][which]
    return dict(ground=p['ground'],yaw=p['yaw'],source='unchanged original v257 request')
def pick(anchor,yaw,used,boundary=False):
    candidates=[r for r in poses if abs(r['pose'][2]-anchor[2])<.09
        and abs(math.remainder(r['pose'][3]-yaw,2*math.pi))<1e-8
        and tuple(round(v,8) for v in r['pose'][:3]) not in used
        and min(r['edge_margin'],r['solid_margin'])>0
        and (not boundary or min(r['edge_margin'],r['solid_margin'])<.08)]
    assert candidates,(anchor,yaw,boundary)
    row=min(candidates,key=lambda r:(math.hypot(r['pose'][0]-anchor[0],r['pose'][1]-anchor[1]),r['key']))
    p=dict(ground=row['pose'][:3],yaw=row['pose'][3],source='original mesh connected pose graph',
           mesh_key=row['key'],edge_margin=row['edge_margin'],solid_margin=row['solid_margin'])
    used.add(xyz(p));return p
def endpoint(p):return np.array(p['ground']+[p['yaw']],float)
def branch(k):
    out=[]
    while k is not None:out.append(k);k=parent[k]
    return out
def witness(a,b,same_floor=False):
    pa,pb=endpoint(a),endpoint(b)
    aa=[k for k in mesh.near(pa) if k in parent];bb=[k for k in mesh.near(pb) if k in parent]
    assert aa and bb,('exact_endpoint_attachment',a,b)
    best=None
    for u in aa:
        bu=branch(u);pos={k:i for i,k in enumerate(bu)}
        for v in bb:
            bv=branch(v);meeting=next((k for k in bv if k in pos),None)
            keys=bu[:pos[meeting]+1]+list(reversed(bv[:bv.index(meeting)])) if meeting is not None else bu+[None]+list(reversed(bv))
            score=len(keys)+np.linalg.norm(mesh.pose(u)[:3]-pa[:3])/mesh.res+np.linalg.norm(mesh.pose(v)[:3]-pb[:3])/mesh.res
            if best is None or score<best[0]:best=score,keys
    path=[pa]+[np.array(root) if k is None else mesh.pose(k) for k in best[1]]+[pb]
    if same_floor and max(p[2] for p in path)-min(p[2] for p in path)>.12:
        neighbours=mesh.neighbours
        low=min(pa[2],pb[2])-.12;high=max(pa[2],pb[2])+.12
        mesh.neighbours=lambda k:(q for q in neighbours(k) if low<=mesh.pose(q)[2]<=high)
        try:result=mesh.search(pa,pb)
        finally:mesh.neighbours=neighbours
        assert result['certified'],('same_floor_mesh_witness',a,b)
        path=[np.array(p,float) for p in result['path']]
    edge=solid=math.inf;count=0
    # Replay all used edges against original triangles, including actual poses.
    for p,q in zip(path,path[1:]):
        ok,samples=mesh.mesh.edge(p,q)
        assert ok,('original_mesh_witness_replay',p,q,samples[-1:] if samples else [])
        count+=len(samples);edge=min(edge,min(s[5] for s in samples));solid=min(solid,min(s[6] for s in samples))
    return dict(certified=True,path=[p.tolist() for p in path],checked_samples=count,
        min_edge_margin=edge,min_solid_margin=solid,source='original finite Newton triangles',
        geometric_only=True,route_scores_used=False)
def add(cid,stratum,a,b,feature):
    used_start.add(xyz(a));used_goal.add(xyz(b))
    r=witness(a,b,stratum=='same_floor')
    f=OUT/'certificates'/f'{cid}.json';f.parent.mkdir(exist_ok=True);f.write_text(json.dumps(r)+'\n')
    c=dict(case_id=cid,stratum=stratum,start=a,goal=b,feature=feature,expected='admit',
        mesh_certificate_sha256=sha(f),mesh_min_edge_margin=r['min_edge_margin'],
        mesh_min_solid_margin=r['min_solid_margin'])
    cases.append(c);print('CONSTRUCT',cid,'samples',r['checked_samples'],flush=True)

for cid in ('A04','G05'):add(cid,'ascent',original(cid,'start'),original(cid,'goal'),'unchanged original hard ascent')
starts=[(-6,6.8),(-5.5,7.4),(-4.5,7.2),(-3.5,8),(-1.5,7.4),(.5,7.5),(2.5,7.3),(4.5,7.6),(6.5,7.5),(8.4,7),(0,8.3),(3.3,8.3),(-4.5,8.3)]
goals=[(5,4),(6,5),(-4,-3.5),(-3,3.7),(1,4),(3,2),(-4,1),(0,-4),(4,-3),(7,-5.5),(8,-6.5),(8,7),(-2,-2)]
headings=[-math.pi/2,-math.pi/4,-3*math.pi/4,0,math.pi,math.pi/2,-math.pi/2,0,math.pi,-math.pi/4,math.pi/4,3*math.pi/4,math.pi]
for k,(s,g,yaw) in enumerate(zip(starts,goals,headings),1):
    add(f'CU{k:02d}','ascent',pick([*s,.058],yaw,used_start),pick([*g,4.533],[0,math.pi/2,math.pi,-math.pi/2][k%4],used_goal),'distinct approach and upper wing; explicit initial yaw')
add('D07','descent',original('D07','start'),original('D07','goal'),'unchanged original terminal-heading regression')
down_s=[(6.3,4.5),(-1,2.5),(-4.5,-3.5),(-4,4.5),(-3,-1),(0,0),(2,3),(4,-3),(0,-4),(4,4),(8,7),(8,-7),(6,-4),(-4,1)]
down_g=[(-5.5,7.2),(-3,7.5),(1,7.6),(-6.3,8),(-4.5,8),(3.5,8),(5.5,7),(7,7.5),(8.5,7),(1,8),(3,8.5),(4.5,8.1),(-1,8.1),(-6,7.5)]
for k,(s,g) in enumerate(zip(down_s,down_g),1):
    add(f'CD{k:02d}','descent',pick([*s,4.533],k*math.pi/4,used_start),pick([*g,.058],(k%4)*math.pi/2,used_goal),'distinct upper start and reverse staircase approach')
mid=[((-4,-4,1.558),(4,3,4.533)),((7.8,6.4,3.058),(-2,3,4.533)),((6.5,-5.9,3.058),(0,7.4,.058)),((0,-4.3,1.558),(7,7.5,.058)),((-5.7,7.5,.058),(-3,-4.2,1.558)),((8,7,4.533),(7.5,6.4,3.058)),((-2,2,4.533),(8,-6,3.058)),((2,7.5,.058),(3,-4.3,1.558))]
for k,(s,g) in enumerate(mid,1):add(f'CM{k:02d}','intermediate',pick(s,k*math.pi/2,used_start),pick(g,(k+1)*math.pi/2,used_goal),'intermediate landing start' if k<=4 else 'intermediate landing goal')
add('S04','same_floor',original('S04','start'),original('S04','goal'),'unchanged original upper wing corner')
same=[((-6,7.4,.058),(-4,8,.058)),((2,8,.058),(7.5,7,.058)),((4,5,4.533),(8,7.5,4.533)),((4,-4.5,4.533),(8,-7,4.533)),((-4,4,4.533),(-4,-4,4.533))]
for k,(s,g) in enumerate(same,1):add(f'CS{k:02d}','same_floor',pick(s,k*math.pi/2,used_start),pick(g,(k+1)*math.pi/2,used_goal),'same-floor pillar/wing opening/corridor corner')
for cid in ('E02','E03'):add(cid,'boundary',original(cid,'start'),original(cid,'goal'),'unchanged original boundary heading regression')
for k,(s,g,z,yaw) in enumerate([((-5,7.5),(-5.9,6.7),.058,math.pi/2),((2,3),(-5.8,4.8),4.533,math.pi/2),((4,-4),(5.8,-5.2),4.533,0),((2,7.5),(6.2,6.7),.058,math.pi)],1):
    add(f'CE{k:02d}','boundary',pick([*s,z],0,used_start),pick([*g,z],yaw,used_goal,True),'low positive original-mesh support or wall clearance')
assert len(cases)==50
tuples=[tuple(c['start']['ground']+[c['start']['yaw']]+c['goal']['ground']+[c['goal']['yaw']]) for c in cases]
assert len(set(tuples))==50
for cid in ('E04','E05','E06'):
    a,b=original(cid,'start'),original(cid,'goal')
    verdict=mesh.mesh.pose(*endpoint(b))
    proposals.append(dict(case_id=cid,endpoint_mesh_verdict=verdict,original_ledger_unchanged=True))
    if not verdict[0]:
        cases.append(dict(case_id='CI_'+cid,stratum='illegal_control',start=a,goal=b,
            feature='unchanged original endpoint with original-mesh hard violation',
            expected='reject',mesh_endpoint_verdict=verdict))
if len(cases)<53:
    # Only explicit original-mesh hard violations qualify as additional illegal
    # endpoints. Graph exhaustion or a native planner refusal is insufficient.
    used_bad={xyz(c['goal']) for c in cases if c['expected']=='reject'}
    for anchor in ((-6.3,6.2,.058),(7.,-3.,4.533),(-6.,-3.2,4.533)):
        bad=[(k,v) for k,v in mesh.states.items() if not v[0]
            and v[3] in ('body_solid','floor_edge') and min(v[1],v[2])<-.02
            and abs(mesh.pose(k)[2]-anchor[2])<.09
            and tuple(round(x,8) for x in mesh.pose(k)[:3]) not in used_bad]
        if not bad:continue
        k,v=min(bad,key=lambda kv:np.linalg.norm(mesh.pose(kv[0])[:3]-anchor))
        p=mesh.pose(k);b=dict(ground=p[:3].tolist(),yaw=float(p[3]),source='original mesh hard violation')
        used_bad.add(xyz(b));cases.append(dict(case_id=f'CI_NEW{len(cases)-49:02d}',stratum='illegal_control',
            start=original('A04','start'),goal=b,expected='reject',feature='mesh-certified illegal boundary endpoint',mesh_endpoint_verdict=v))
        if len(cases)>=53:break
assert len(cases)>=53
(OUT/'construction_proposals.json').write_text(json.dumps(proposals,indent=2)+'\n')
template=json.loads((EXP/'inputs/historical_full_building.json').read_text())
for c in cases:
    folder=OUT/'cases'/c['case_id'];folder.mkdir(parents=True,exist_ok=False)
    scenario=dict(template);scenario.update(case_id=c['case_id'],route_profile='generalization',spawn_ground_xyz_m=c['start']['ground'],spawn_yaw_rad=c['start']['yaw'],goal_ground_xyz_m=c['goal']['ground'],goal_yaw_rad=c['goal']['yaw'],profile_source='v262 original-mesh certified pre-score construction',scene_condition='Complete original Building; no actor')
    for key in ('native_support_screen','initial_center_distance_m','initial_placement_pass'):scenario.pop(key,None)
    (folder/'scenario.json').write_text(json.dumps(scenario,indent=2)+'\n')
    values=c['start']['ground'][:2]+[c['start']['ground'][2]+.3]+c['goal']['ground'][:2]+[c['goal']['ground'][2]+.3,c['start']['yaw'],c['goal']['yaw']]
    (folder/'endpoints.txt').write_text(' '.join(map(str,values))+'\n')
    c.update(scenario_sha256=sha(folder/'scenario.json'),endpoints_sha256=sha(folder/'endpoints.txt'))
manifest=dict(version='v262',cases=cases,positive_count=50,illegal_controls=len(cases)-50,distinct_positive_tuples=50,distinct_spatial_pairs=len({tuple(c['start']['ground']+c['goal']['ground']) for c in cases if c['expected']=='admit'}),frozen_before_route_scoring=True,original_mesh_sha256=sha(tri),mesh_component_receipt_sha256=sha(OUT/'component_receipt.json'),construction_source_sha256=sha(Path(__file__)),native_results_read=False,hard_radius_m=.35,sensor_period_s=.1,scope='original-mesh body/support geometry; not dynamics',source_geometry_limit='open halls, wing openings and pillars; no invented door leaves or rooms')
(OUT/'cases_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('CONSTRUCTION_COMPLETE',len(cases),flush=True)
