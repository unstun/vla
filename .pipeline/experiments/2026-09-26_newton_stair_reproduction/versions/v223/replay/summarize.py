"""Exact counts with separate first-rejection and overlapping predicate ledgers."""
from pathlib import Path
import csv,json,collections,hashlib
root=Path('/data/sun/vla_mppi_20261009')
work=root/'floor_reason_v223'
old=root/'stair_collision_replay_20261016/output'

def rows(path):
    with path.open() as stream:return list(csv.DictReader(stream))
def tally(data):
    rejected=[r for r in data if int(r['native'])]
    first=collections.Counter();intersections=collections.Counter();counts=collections.Counter()
    for r in rejected:
        first[str(int(r['front_reason']) or int(r['rear_reason']))]+=1
        edge=int(r['edge_guard'])!=0
        occupied=int(r['cylinder_occupied'])!=0
        history=occupied and int(r['history_101'])!=0
        extra=occupied and not int(r['torso_occupied'])
        intersections[f'edge={int(edge)},history={int(history)},extra={int(extra)}']+=1
        counts['edge_guard']+=edge;counts['history_101_effective']+=history
        counts['history_target_effective']+=occupied and int(r['history_target'])!=0
        counts['cylinder_occupied']+=occupied;counts['torso_occupied']+=int(r['torso_occupied'])!=0
        counts['cylinder_extra_same_map']+=extra
        counts['solid_other_effective']+=occupied and int(r['other_occupied'])!=0
        counts['torso_swap_would_clear_with_support_unchanged']+=extra and all(int(r[k]) in (0,107) for k in ('front_reason','rear_reason'))
        counts['unknown_occupancy']+=int(r['unknown'])!=0
    return {'queries':len(data),'rejected':len(rejected),'first_reason':dict(first),'independent_predicates':dict(counts),'exclusive_intersections':dict(intersections)}

result={'physics_steps':0,'scope':'Yaw-matched torso-vs-cylinder same-map voxel audit; no leg-contact or execution claim','datasets':{}}
for dataset,prior in [('input','native_details'),('critical_input','critical_native')]:
    folder=work/'replay_output02'/dataset;data=rows(folder/'attribution.csv')
    mismatches=0
    for p in folder.glob('frame_*.csv'):
        before=rows(old/prior/p.name);after=rows(p)
        assert len(before)==len(after)
        for a,b in zip(before,after):
            assert all(a[k]==b[k] for k in ('id','kind','x','y','z','yaw')),(p,a,b)
            mismatches+=bool(int(a['native']))!=bool(int(b['native']))
    result['datasets'][dataset]={'binary_changes_vs_v219':mismatches,'all':tally(data),'by_kind':{str(k):tally([r for r in data if int(r['kind'])==k]) for k in sorted({int(r['kind']) for r in data})}}
    if dataset=='critical_input':result['critical_queries']=data
result['artifacts']={str(p.relative_to(work)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (work/'replay_output02').rglob('*.csv')}
(work/'attribution_summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='artifacts'},indent=2))
