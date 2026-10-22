"""Freeze first nearby pose meeting construction rules, before route scoring."""
from pathlib import Path
import csv,hashlib,json

BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'generalization_v242'
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    candidates=json.loads((OUT/'discovery/candidates.json').read_text())
    screen={r['id']:r for r in csv.DictReader((OUT/'discovery/native/screen.csv').open())}
    selected={};decisions=[]
    for item in candidates:
        r=screen[item['id']];boundary=item['anchor'] in ('B08_g','B09_g')
        valid=(int(r['static_verdict'])==0 and int(r['floor_known'])==1 and
               float(r['edge_margin'])>=0 and (boundary or float(r['atlas_solid_margin'])>=0))
        choose=valid and item['anchor'] not in selected
        decisions.append(dict(**item,screen=r,construction_valid=valid,selected=choose))
        if choose:selected[item['anchor']]=item
    missing=sorted(set(r['anchor'] for r in candidates)-set(selected))
    (OUT/'discovery/selection_ledger.json').write_text(json.dumps(dict(decisions=decisions,missing=missing),indent=2)+'\n')
    if missing:raise RuntimeError(f'Construction lacks valid anchor: {missing}')
    template=json.loads((HERE.parents[1]/'inputs/historical_full_building.json').read_text())
    cases=[]
    for name in ['A01','A02','A03','A04','G05','G06','G07','B08','B09','R10','R11','R12']:
        a,b=selected[name+'_s'],selected[name+'_g'];scenario=dict(template)
        scenario.update(spawn_ground_xyz_m=a['ground'],spawn_yaw_rad=a['yaw'],
            goal_ground_xyz_m=b['ground'],route_profile='generalization',case_id=name,
            profile_source='v242 frozen map candidates; no route result used for selection',
            scene_condition='Complete original Building; new endpoint case; no actor')
        scenario.pop('native_support_screen',None)
        scenario.pop('initial_center_distance_m',None)
        scenario.pop('initial_placement_pass',None)
        folder=OUT/'cases'/name;folder.mkdir(parents=True,exist_ok=False)
        p=folder/'scenario.json';p.write_text(json.dumps(scenario,indent=2)+'\n')
        endpoints=a['ground'][:2]+[a['ground'][2]+.3]+b['ground'][:2]+[b['ground'][2]+.3,a['yaw']]
        (folder/'endpoints.txt').write_text(' '.join(map(str,endpoints))+'\n')
        cases.append(dict(case_id=name,start=a,goal=b,scenario_sha256=sha(p),
            scenario_remote=str(p),direction='descent' if name.startswith('R') else 'same_floor' if name=='B09' else 'ascent'))
    manifest=dict(version='v242',frozen_before_scoring=True,calls_per_case=5,cases=cases,
        construction='first nearest valid candidate in predeclared geometric order; no route scoring',
        artifacts={str(p.relative_to(OUT)):sha(p) for p in (OUT/'discovery').rglob('*') if p.is_file()},
        parent='v240',rl_sha256='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b')
    with (OUT/'cases_manifest.json').open('x') as f:json.dump(manifest,f,indent=2);f.write('\n')
    print(json.dumps(cases,indent=2))

if __name__=='__main__':main()
