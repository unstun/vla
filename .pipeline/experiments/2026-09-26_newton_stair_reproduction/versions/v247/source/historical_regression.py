from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,time
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'physical_traversability_v247/evaluation'
spec=importlib.util.spec_from_file_location('candidate_metrics',HERE/'run_matrix.py');adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
fixture=BASE/'physical_traversability_v247/historical/cases/H00'
identity=json.loads((fixture/'fixture.json').read_text())
assert identity['physics_steps']==0 and identity['max_scan_s']<=.1
for n,h in identity['files'].items():assert hashlib.sha256((fixture/n).read_bytes()).hexdigest()==h,n
tag=os.environ.get('V247_HISTORICAL_TAG','historical02');target=OUT/tag;target.mkdir(exist_ok=False);began=time.monotonic()
with (target/'stdout.log').open('x') as log:
 code=subprocess.run([sys.executable,str(HERE/'probe.py'),'/task/physical_traversability_v247/historical/cases/H00','/evaluation/'+tag],stdout=log,stderr=subprocess.STDOUT,timeout=150).returncode
row=adapter.summarize(target,code,time.monotonic()-began);row['case_id']='H00';row['fixture_sha256']=hashlib.sha256((fixture/'fixture.json').read_bytes()).hexdigest()
(target/'summary.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True)
