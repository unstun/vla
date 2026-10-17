"""Produce compact, traceable measurements from native replay outputs."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
ROOT=Path('/data/sun/vla_mppi_20261009/stair_collision_replay_20261016')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return list(csv.DictReader(p.open()))
frames=json.loads((ROOT/'input/frames.json').read_text())
result={'scope':'Ordered captured-input collision replay; no new planner/physics episode.','frames':[],'queries':0,'parity_errors':0,'all_query_coordinates_equal':True,'detail_observer_decisions_unchanged':True}
counts=Counter();hashes={}
for f in frames:
    i=f['index'];paths={name:ROOT/'output'/name/f'frame_{i}.csv' for name in ['native','native_details','original_author','original_current']}
    data={name:read(p) for name,p in paths.items()}
    assert paths['native'].read_bytes()==paths['native_details'].read_bytes()
    for name,rows in data.items():
        assert len(rows)==len(data['native'])
        for a,b in zip(rows,data['native']):
            assert all(a[k]==b[k] for k in ['id','kind','x','y','z','yaw'])
        hashes[str(paths[name].relative_to(ROOT))]=sha(paths[name])
    n=data['native'];body=n[0];route=[x for x in n if x['kind']=='1']
    row={'frame':i,'time_s':f['time_s'],'cloud_ns':f['last_cloud_stamp_ns'],'body':body,'body_original_author':data['original_author'][0]['blocked'],'body_original_current':data['original_current'][0]['blocked'],'query_count':len(n),'route_queries':len(route),'route_native_free':sum(x['native']=='0' for x in route)}
    for name,rows in data.items():
        field='native' if name.startswith('native') else 'blocked'
        row[name+'_free']=sum(x[field]=='0' for x in rows)
    result['frames'].append(row);result['queries']+=len(n)
    counts.update(str(int(x['front_reason'])) for x in n if x['native']!='0')
result['front_reason_counts_for_blocked_queries']=dict(counts)
result['parity_errors']=sum(int(x['parity_errors']) for x in read(ROOT/'output/native/frames.csv'))
critical=json.loads((ROOT/'critical_input/identity.json').read_text())
result['exact_logged_queries']=[]
for f in critical['frames']:
    i=f['frame'];r=dict(f)
    for mode in ['native','original_author','original_current']:r[mode]=read(ROOT/'output'/('critical_'+mode)/f'frame_{i}.csv')[0]
    r['details']=[x for x in read(ROOT/'output/critical_native/details.csv') if int(x['frame'])==i]
    result['exact_logged_queries'].append(r)
result['geometry']=json.loads((ROOT/'output/geometry_check.json').read_text())
result['support_guard_log']=(ROOT/'logs/support_probe01.log').read_text()
result['input_identity_sha256']=sha(ROOT/'input/identity.json')
result['critical_identity_sha256']=sha(ROOT/'critical_input/identity.json')
result['native_details_sha256']=sha(ROOT/'output/native_details/details.csv')
result['native_body_free']=sum(f['body']['native']=='0' for f in result['frames'])
result['original_author_body_free']=sum(f['body_original_author']=='0' for f in result['frames'])
result['original_current_body_free']=sum(f['body_original_current']=='0' for f in result['frames'])
result['first_wrong_height']=next(f for f in result['frames'] if f['body']['front_reason']=='110')
result['inputs']={p.name:sha(p) for p in (ROOT/'input').glob('*') if p.is_file()}
result['artifacts']=hashes
(ROOT/'output/summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['queries','parity_errors','native_body_free','original_author_body_free','original_current_body_free','first_wrong_height']},indent=2))
