"""Freeze cases, per-start captures and evaluator before exactly-once scoring."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'space_coverage_v257';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'manifest.json').exists() and not (OUT/'scored').exists()
native=HERE.parent/'v256';assert json.loads((native/'manifest.json').read_text())['frozen']
d=json.loads((HERE/'cases_manifest.json').read_text());assert sha(HERE/'cases_manifest.json')==sha(OUT/'cases_manifest.json') and len(d['cases'])==52
fixtures={}
for c in d['cases']:
 p=OUT/'cases'/c['case_id'];f=p/'fixture.json';value=json.loads(f.read_text());assert value['physics_steps']==0 and value['max_scan_s']<=.1 and value['scenario_sha256']==c['scenario_sha256']
 assert sha(p/'scenario.json')==c['scenario_sha256'] and sha(p/'endpoints.txt')==c['endpoints_sha256']
 for rel,h in value['files'].items():assert sha(p/rel)==h,(c['case_id'],rel)
 fixtures[c['case_id']]=sha(f)
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and p.relative_to(HERE).parts[0] not in ('source','results','__pycache__') and p.name not in ('manifest.json','RESULTS.md') and '__pycache__' not in p.parts}
for rel in files:
 p=HERE/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/rel,p)
manifest=dict(version='v257',frozen=True,native='v256',native_manifest_sha256=sha(native/'manifest.json'),source_files=files,cases_manifest_sha256=sha(HERE/'cases_manifest.json'),fixtures=fixtures,policy_golden_sha256=sha(OUT/'policy_golden.json'),native_probe_sha256=sha(OUT/'build/native_probe'),raw_reference_library_sha256=sha(OUT/'build/libraw_reference.a'),calls_per_case=1,cases=52,physics_steps=0,terminal_heading='explicit RouteSession infer_heading=false',hard_radius_m=.35,sensor_period_s=.1,scope='Frozen evaluation protocol; no acceptance promotion')
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest),flush=True)
