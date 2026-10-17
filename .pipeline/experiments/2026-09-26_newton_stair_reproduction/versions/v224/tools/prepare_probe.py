"""Bind the field to the existing terrain package and generate a candidate profile."""
from pathlib import Path
import hashlib,json,csv
import yaml
from lite3_nav2_bridge.profile import write_profile
from lite3_nav2_bridge.terrain_bundle import fnv64
work=Path('/work');root=Path('/task');building=work/'fixtures/building'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
field=building/'environment03.env';terrain=building/'terrain.json'
metadata={'format':'ENV224B','file':field.name,'sha256':sha(field),'fnv64':fnv64(field.read_bytes()),
 'terrain_manifest_sha256':sha(terrain),'static_pcd_sha256':'8721efeb74415336d47c97d861d6e30ad213669b120d5b37c62461100c1f2eae',
 'source':'pinned Building PCD; production native terrain classifier; physical-floor edge guard; ETH step scores',
 'scope':'static soft cost only; no live free-space or motion authorization','target_margin_m':.15}
pcd=root/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/inputs/static_background/building2_9.pcd'
assert sha(pcd)==metadata['static_pcd_sha256']
manifest=building/'environment03.json'
if manifest.exists():
 assert json.loads(manifest.read_text())==metadata
else:manifest.write_text(json.dumps(metadata,indent=2)+'\n')
profile=work/'fixtures/environment_candidate03.yaml'
write_profile(profile,root/'stair_collision_replay_20261016/input/planner.yaml',True,terrain_manifest=terrain,environmental_manifest=manifest)
# Exact body and route/seed diagnostic queries; do not flood the benchmark with the synthetic surface grid.
rows=list(csv.DictReader((root/'floor_reason_v223/replay_output02/input/attribution.csv').open()))
queries=[r for r in rows if r['kind']!='2']
(work/'fixtures/bench_poses.txt').write_text(''.join(' '.join(r[k] for k in ['x','y','z','yaw'])+'\n' for r in queries))
# Read the original reference saved by the replay preparation, without numpy dependency in ROS Python.
import struct
path=root/'stair_collision_replay_20261016/input/route_0000.npy'
with path.open('rb') as stream:
 assert stream.read(6)==b'\x93NUMPY';major,minor=stream.read(2)
 n=struct.unpack('<H' if major==1 else '<I',stream.read(2 if major==1 else 4))[0]
 import ast
 header=ast.literal_eval(stream.read(n).decode());assert header['descr']=='<f8' and not header['fortran_order']
 data=struct.unpack('<'+'d'*(header['shape'][0]*3),stream.read())
(work/'fixtures/route_endpoints.txt').write_text(' '.join(map(str,data[:3]+data[-3:]))+'\n')
(work/'fixtures/probe03.env').write_text('export ENVIRONMENT_INPUT=/work/fixtures/building/environment03.env\nexport ENVIRONMENT_FNV='+metadata['fnv64']+'\n')
print(json.dumps({'field':metadata,'candidate_profile':str(profile),'benchmark_queries':len(queries)},indent=2))
