"""Uniform geometry-only start replacement; never read route scores."""
from pathlib import Path
import argparse, copy, csv, hashlib, json, math, pickle, sys
import numpy as np

HERE=Path(__file__).resolve().parent;EXP=HERE.parents[1]
BASE=Path('/data/sun/vla_mppi_20261009');OUT=Path('/home/sun/vla_exec/local_cost_crash_v288/cohort')
OLD=BASE/'mesh_benchmark_v262';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2)+'\n')

def propose():
    assert not (OUT/'cases_manifest.json').exists()
    old=json.loads((HERE.parent/'v281/clean50.json').read_text())
    poses=json.loads((OLD/'reachable_poses.json').read_text());rows=[];groups={}
    for c in old['cases']:
        if c['expected']!='admit':continue
        start=c['start'];origin=np.array(start['ground']);yaw=start['yaw']
        candidates=[p for p in poses if abs(p['pose'][2]-origin[2])<.09
            and abs(math.remainder(p['pose'][3]-yaw,2*math.pi))<1e-8
            and min(p['edge_margin'],p['solid_margin'])>=.10]
        candidates.sort(key=lambda p:(math.hypot(p['pose'][0]-origin[0],p['pose'][1]-origin[1]),p['key']))
        selected=[dict(ground=start['ground'],yaw=yaw,source='unchanged original start')]
        selected += [dict(ground=p['pose'][:3],yaw=yaw,source='connected original geometry',mesh_key=p['key']) for p in candidates[:128]]
        groups[c['case_id']]=[]
        for i,p in enumerate(selected):
            key=f"{c['case_id']}_{i:03d}";groups[c['case_id']].append(key)
            rows.append(dict(id=key,case_id=c['case_id'],candidate=p))
    OUT.mkdir(parents=True,exist_ok=True)
    save(OUT/'proposals.json',dict(original_sha256=sha(HERE.parent/'v281/clean50.json'),groups=groups,rows=rows,route_scores_used=False))
    with (OUT/'queries.txt').open('w') as f:
        for r in rows:
            p=r['candidate'];f.write(' '.join(map(str,[r['id']]+p['ground'][:2]+[p['ground'][2]+.3,p['yaw']]))+'\n')
    print(json.dumps(dict(stage='proposed',legal_starts=len(groups),queries=len(rows))))

def construct():
    assert not (OUT/'cases_manifest.json').exists()
    proposal=json.loads((OUT/'proposals.json').read_text());margins={r['id']:r for r in csv.DictReader((OUT/'margins.csv').open())}
    assert len(margins)==len(proposal['rows'])
    rows={r['id']:r['candidate'] for r in proposal['rows']}
    old=json.loads((HERE.parent/'v281/clean50.json').read_text());assert sha(HERE.parent/'v281/clean50.json')==proposal['original_sha256']
    # Reuse only the original mesh constructor's definitions, before its case
    # selection loops. Its graph and source-triangle certificate stay unchanged.
    source=(HERE.parent/'v262/construct.py').read_text().split("for cid in ('A04','G05'):")[0]
    source=source.replace("assert not (OUT/'cases_manifest.json').exists()",'')
    ns=dict(__file__=str(HERE.parent/'v262/construct.py'),__name__='geometry_certificate_only')
    exec(compile(source,'v262_certificate_definitions','exec'),ns)
    witness=ns['witness'];cases=[];changes=[];used=set()
    for original in old['cases']:
        c=copy.deepcopy(original);cid=c['case_id'];changed=False
        if c['expected']=='admit':
            ids=proposal['groups'][cid]
            eligible=[k for k in ids if int(margins[k]['support_verdict'])==0
                and min(float(margins[k]['edge_margin']),float(margins[k]['solid_margin']))>=.10]
            chosen=None
            for key in eligible:
                candidate=rows[key];pair=tuple(candidate['ground']+c['goal']['ground'])
                if pair in used:continue
                if key==ids[0]:chosen=key;break
                try:certificate=witness(candidate,c['goal'],c['stratum']=='same_floor')
                except AssertionError:continue
                chosen=key;save(OUT/'certificates'/f'{cid}.json',certificate);break
            if chosen is None:raise RuntimeError(f'No geometry-certified qualifying start for {cid}')
            changed=chosen!=ids[0]
            if changed:
                c['original_start']=c['start'];c['start']=rows[chosen]
                c['feature']+='; start replaced by uniform >=0.10 m geometry admission'
                c.update(mesh_certificate_sha256=sha(OUT/'certificates'/f'{cid}.json'),
                    mesh_min_edge_margin=certificate['min_edge_margin'],mesh_min_solid_margin=certificate['min_solid_margin'])
            c['start_admission']=dict(required_extra_margin_m=.10,**margins[chosen])
            used.add(tuple(c['start']['ground']+c['goal']['ground']))
            changes.append(dict(case_id=cid,changed=changed,original_start=original['start'],start=c['start'],
                old_admission=margins[ids[0]],new_admission=margins[chosen]))
        folder=OUT/'cases'/cid;folder.mkdir(parents=True,exist_ok=False)
        scenario=json.loads((OLD/'cases'/cid/'scenario.json').read_text())
        scenario.update(spawn_ground_xyz_m=c['start']['ground'],spawn_yaw_rad=c['start']['yaw'])
        save(folder/'scenario.json',scenario)
        values=c['start']['ground'][:2]+[c['start']['ground'][2]+.3]+c['goal']['ground'][:2]+[c['goal']['ground'][2]+.3,c['start']['yaw'],c['goal']['yaw']]
        (folder/'endpoints.txt').write_text(' '.join(map(str,values))+'\n')
        c.update(scenario_sha256=sha(folder/'scenario.json'),endpoints_sha256=sha(folder/'endpoints.txt'))
        if not changed:
            assert sha(folder/'endpoints.txt')==sha(OLD/'cases'/cid/'endpoints.txt')
            # Stationary captured fixtures have identical requested geometry.
            for p in (OLD/'cases'/cid).iterdir():
                if p.is_file() and p.name not in ('scenario.json','endpoints.txt','fixture.json'):
                    import shutil
                    shutil.copy2(p,folder/p.name)
            f=json.loads((OLD/'cases'/cid/'fixture.json').read_text())
            f['scenario_sha256']=c['scenario_sha256'];f['files']['scenario.json']=c['scenario_sha256']
            f['files']['endpoints.txt']=c['endpoints_sha256'];save(folder/'fixture.json',f)
        cases.append(c)
    positives=[c for c in cases if c['expected']=='admit'];negatives=[c for c in cases if c['expected']=='reject']
    assert len(positives)==len(used)==50 and len(negatives)==3
    physical=['A04','G05','CU06','D07','S04','CD12','CM02','CM07','CS03','CE03']
    save(OUT/'start_admission.json',dict(rows=changes,rule='Both authoritative extra margins >=0.10 m; geometry-only deterministic nearest candidate',route_scores_used=False))
    save(OUT/'cases_manifest.json',dict(version='v288',cases=cases,positive_count=50,illegal_controls=3,
        distinct_positive_tuples=50,distinct_spatial_pairs=50,physical_cases=physical,
        original_cohort_sha256=proposal['original_sha256'],hard_radius_m=.35,sensor_period_s=.1,
        frozen_before_route_scoring=True,construction_source_sha256=sha(Path(__file__))))
    print(json.dumps(dict(stage='constructed',cases=len(cases),replaced=[r['case_id'] for r in changes if r['changed']])))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('propose','construct'));a=p.parse_args()
    (propose if a.mode=='propose' else construct)()
