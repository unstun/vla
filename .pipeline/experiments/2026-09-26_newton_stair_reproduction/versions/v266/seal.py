"""Seal independent component evidence only; no native or physical acceptance."""
from pathlib import Path
import hashlib,importlib.metadata as metadata,json,math,shutil,sys
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');WORK=BASE/'source_surface_v266'
sys.path.insert(0,str(BASE/'floor_reason_v223/analysis_deps'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=json.loads((WORK/'surface_validation.json').read_text());b=json.loads((WORK/'primitive_oracle.json').read_text())
assert a['random_fcl_queries']==3300 and not a['fcl_mismatches']
assert b['queries']==4004 and not b['mismatches'] and b['height_translation_cases']==400 and b['sloped_cap_height_band_controls']==4
assert b['model_sha256']==sha(HERE/'surface_model.py')
assert b['oracle_script_sha256']==sha(HERE/'validate_primitive_oracle.py')
assert a['invalid_query_rejected'] and not a['adopted_by_planner']
assert len(a['endpoints'])==8
assert all(r['assessment']['free'] for r in a['endpoints'] if r['case_id']!='B08')
assert not next(r for r in a['endpoints'] if r['case_id']=='B08')['assessment']['free']
R=HERE/'results';R.mkdir(exist_ok=True)
for name in ('source_inspection.json','surface_validation.json','primitive_oracle.json','primitive03.log','validate03.log'):
    shutil.copy2(WORK/name,R/name)
deps={}
for name in ('python-fcl','shapely','numpy','scipy'):
    dist=metadata.distribution(name);deps[name]=dict(version=dist.version,metadata_sha256=hashlib.sha256(dist.read_text('METADATA').encode()).hexdigest(),license=dist.metadata.get('License'),project_urls=dist.metadata.get_all('Project-URL'))
def strict(v):
    if isinstance(v,float) and not math.isfinite(v):return None
    if isinstance(v,list):return [strict(x) for x in v]
    if isinstance(v,dict):return {k:strict(x) for k,x in v.items()}
    return v
summary=dict(version='v266',scope='Independent finite source-surface validation; no planner integration',
    source_triangles_sha256=a['source_triangles_sha256'],radius_m=.35,offset_m=.18,
    synthetic_controls=len(a['synthetic_controls']),surface_fcl_queries=3300,filled_primitive_fcl_queries=4004,
    height_translation_cases=400,sloped_cap_band_controls=4,all_fcl_mismatches=0,
    fixed_endpoints=a['endpoints'],dependencies=deps,planning_calls=0,physics_steps=0,
    selected_baseline_unchanged='v232/v233',known_limits=[a['caveat'],'Python view construction is diagnostic and not a realtime implementation.','Old positive/negative voxel margins and both prior matrix ledgers remain unchanged.'])
(R/'summary.json').write_text(json.dumps(strict(summary),indent=2,allow_nan=False)+'\n')
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ('manifest.json','RESULTS.md')}
manifest=dict(version='v266',scope='independent_source_surface_component_only',native_integrated=False,physical_attempts=0,files=files)
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(version='v266',queries=7304,translation_controls=400,source_endpoints_free=7,b08_refused=True,native_integrated=False,manifest_sha256=sha(HERE/'manifest.json'))))
