"""Bind the atlas, retain exact original queries and add seeded interpolation probes."""
from pathlib import Path
import csv,hashlib,json,math,random
from lite3_nav2_bridge.profile import write_profile
from lite3_nav2_bridge.terrain_bundle import fnv64

work=Path('/work');parent=Path('/task/environment_score_v224');building=work/'fixtures/building'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
field=building/'environment225.env';terrain=building/'terrain.json'
with field.open('rb') as stream:
    assert stream.readline().startswith(b'ENV225 ')
    n=int(stream.readline().split()[1])
    for _ in range(n):stream.readline()
    atlas=stream.readline().decode().split();assert atlas[0]=='A'
metadata={'format':'ENV225','file':field.name,'sha256':sha(field),'fnv64':fnv64(field.read_bytes()),
    'terrain_manifest_sha256':sha(terrain),'static_pcd_sha256':'8721efeb74415336d47c97d861d6e30ad213669b120d5b37c62461100c1f2eae',
    'raw_field_sha256':'72142fda10deec9cfabab95f5d27d1159fa8ec3821f1a808f4a6a1f8186edaac',
    'source':'v224 frozen single-cylinder PCD geometry, original physical-floor edge and ETH channels',
    'scope':'interpolated static soft prior; original hard admission retained','target_margin_m':.15,
    'atlas_spacing_xyz_m':[float(atlas[1]),float(atlas[1]),float(atlas[2])],
    'atlas_origin':[float(v) for v in atlas[3:6]],'atlas_shape':[int(v) for v in atlas[6:9]]}
manifest=building/'environment225.json'
if manifest.exists():assert json.loads(manifest.read_text())==metadata
else:manifest.write_text(json.dumps(metadata,indent=2)+'\n')
profile=work/'fixtures/environment_candidate225.yaml'
if not profile.exists():
    write_profile(profile,'/task/stair_collision_replay_20261016/input/planner.yaml',True,
        terrain_manifest=terrain,environmental_manifest=manifest)
else:
    import yaml
    profile_data=yaml.safe_load(profile.read_text())['planner_server']['ros__parameters']['PCT']
    assert profile_data['environmental_path']==str(field) and profile_data['environmental_fnv64']==metadata['fnv64']

poses=[]
for line in (work/'fixtures/bench_poses.txt').read_text().splitlines():poses.append((0,*map(float,line.split())))
for group,name in enumerate(('legacy_graph','shared_graph','legacy_route','shared_route'),1):
    for row in csv.DictReader((parent/'field_probe_output06'/f'{name}.csv').open()):
        poses.append((group,*(float(row[k]) for k in ('x','y','z','yaw'))))
rng=random.Random(225);recorded=list(poses)
for _ in range(3000):
    _,x,y,z,yaw=rng.choice(recorded)
    poses.append((5,x+rng.uniform(-.035,.035),y+rng.uniform(-.035,.035),z+rng.uniform(-.05,.05),yaw+rng.uniform(-math.pi,math.pi)))
for _ in range(2000):
    poses.append((6,rng.uniform(-7.5,10.5),rng.uniform(-9.,8.5),rng.uniform(.05,6.65),rng.uniform(-math.pi,math.pi)))
(work/'fixtures/oracle_poses225.txt').write_text(''.join(' '.join(map(str,p))+'\n' for p in poses))
(work/'fixtures/probe225.env').write_text(
    'export ENVIRONMENT_INPUT=/work/fixtures/building/environment225.env\nexport ENVIRONMENT_FNV='+metadata['fnv64']+
    '\nexport RAW_FIELD=/task/environment_score_v224/fixtures/building/environment03.env\nexport RAW_FNV=4316416882194453309'+
    '\nexport ATLAS_AZ='+str(metadata['atlas_origin'][2])+'\n')
print(json.dumps({'atlas':metadata,'oracle_poses':len(poses),'physics_steps':0},indent=2))
