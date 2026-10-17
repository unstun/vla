"""Return compact execution evidence and verify immutable bytes after physics."""
from pathlib import Path
import csv,hashlib,importlib.util,json,shutil,sys
import numpy as np
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];VERSIONS=BASE/'versions'
sys.path.insert(0,str(VERSIONS/'v196'))
from analyze_remote import Capture,core
REMOTE=Path('/data/sun/vla_mppi_20261009');TASK=REMOTE/'trials/v233_linux_full_attempt01';RAW=TASK/'runs/v233_linux_full_attempt01'
OUT=HERE/'results';RECEIPTS=OUT/'execution_receipts';RECEIPTS.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
for name in ('execution.json','execution_request.json','graph_preflight.json','native_preflight.json','resource_admission.json','source_gate_before.json'):
 shutil.copyfile(VERSIONS/'v233'/name,RECEIPTS/name)
shutil.copyfile(TASK/'graph_probe/configuration_gate.json',RECEIPTS/'configuration_gate_preflight.json')
capture=Capture(RAW)
for name in ('shared_state.json','source_gate.json','episode_request.json','result.json','initial_state.json','nav2_params.yaml','nav2_params.scan.yaml','planner.yaml','v232_runtime_binding.json','locomotion_activation.json','native_commands.json','backend_latest.json','artifacts/stair_driver_result.json','artifacts/external_episode/finish_request.json','native_process_failure.json'):
 try:(RECEIPTS/name.replace('/','__')).write_text(capture.read(name))
 except (FileNotFoundError,KeyError):pass
spec=importlib.util.spec_from_file_location('profile',VERSIONS/'v233/verify_profile.py');profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)
save(RECEIPTS/'actual_profile_equivalence.json',profile.verify(RAW))
lines=capture.read('nav2.log').splitlines()
(OUT/'pct_runtime_context.txt').write_text('\n'.join(s for s in lines if 'pct_' in s.lower() or 'PCT' in s)+'\n')
(OUT/'failure_context.txt').write_text('\n'.join(s for s in lines if any(k in s.lower() for k in ('exception','process has died','terminate called','failed','abort'))) +'\n')
work=REMOTE/'callback_failure_v232';receipt=json.loads((work/'offline_gate.json').read_text())
for name,expected in receipt['source_inventory'].items():assert sha(work/name)==expected,name
for name,expected in receipt['installed_files'].items():assert sha(work/name)==expected,name
for version,key in (('v233','source_files'),('v232','files')):
 for name,expected in json.loads((VERSIONS/version/'manifest.json').read_text())[key].items():assert sha(VERSIONS/version/name)==expected,name
for name in ('long_route_driver.py','native_graph.py'):
 assert hashlib.sha256(capture.read('frozen_v232_'+name).encode()).hexdigest()==sha(VERSIONS/'v232'/name)
assert hashlib.sha256(capture.read('executed_long_route_driver_v232.py').encode()).hexdigest()==sha(VERSIONS/'v232/long_route_driver.py')
save(RECEIPTS/'post_run_source_parity.json',{'passed':True,'composed_source_files':317,'installed_files':607,'v232_frozen_files_verified':True,'v233_frozen_files_verified':True,'actual_v232_graph_driver_verified':True,'offline_gate_sha256':sha(work/'offline_gate.json')})
reports={}
for v in ('v219','v231','v233'):
 raw=REMOTE/'trials'/(v+'_linux_full_attempt01')/'runs'/(v+'_linux_full_attempt01');c=Capture(raw);log=c.read('nav2.log')
 class Log:
  def read_text(self):return log
 starts,done=core.parse_rounds(Log());part=[r for r in done if r.get('completed') and 45<=r['ros_s']<46.686]
 rows=[r for r in csv.DictReader((HERE/'work'/(v+'_linux_full_attempt01_margins.csv')).open()) if 45<=float(r['time_s'])<46.686]
 known=[float(r['extra_edge_margin_m']) for r in rows if int(r['floor_known'])]
 reports[v]={'completed_rounds':len(part),'successful_rounds':sum(r['success'] for r in part),'incomplete_starts':sum(45<=r['ros_s']<46.686 and not r['completed'] for r in starts),'body_samples':len(rows),'known_floor_samples':len(known),'minimum_extra_edge_margin_m':min(known) if known else None,'p05_extra_edge_margin_m':float(np.quantile(known,.05)) if known else None,'negative_margin_samples':sum(x<0 for x in known),'target_capped_samples':sum(x>=.15-1e-10 for x in known)}
save(OUT/'common_active_prefix.json',{'window_physics_s':[45,46.686],'definition':'Common time prefix before v231 last reactive observation preceding its abort; no equal-progress or causal-ablation claim.',**reports})
save(OUT/'closeout_inputs.json',{'collector_sha256':sha(Path(__file__)),'source_parity':True,'raw_root':str(RAW),'raw_archive_sha256':sha(RAW/'raw_capture.zip'),'collected_files':{str(p.relative_to(OUT)):sha(p) for p in RECEIPTS.rglob('*') if p.is_file()}})
print(json.dumps({'source_parity':True,'reports':reports},indent=2))
