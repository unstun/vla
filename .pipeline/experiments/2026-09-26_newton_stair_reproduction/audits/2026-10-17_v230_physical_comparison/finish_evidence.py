"""Compact closeout receipts and equally observed pre-crash comparison; no physics."""
from pathlib import Path
import csv,hashlib,json,shutil,sys
import numpy as np
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];VERSIONS=BASE/'versions'
sys.path.insert(0,str(VERSIONS/'v196'))
from analyze_remote import Capture,core
REMOTE=Path('/data/sun/vla_mppi_20261009');TASK=REMOTE/'trials/v231_linux_full_attempt01';RAW=TASK/'runs/v231_linux_full_attempt01'
OUT=HERE/'results';RECEIPTS=OUT/'execution_receipts';RECEIPTS.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
for name in ('execution.json','execution_request.json','graph_preflight.json','native_preflight.json','resource_admission.json','source_gate_before.json'):
 shutil.copyfile(VERSIONS/'v231'/name,RECEIPTS/name)
for name in ('configuration_gate.json',):shutil.copyfile(TASK/'graph_probe'/name,RECEIPTS/name)
capture=Capture(RAW)
for name in ('shared_state.json','source_gate.json','episode_request.json','result.json','initial_state.json','nav2_params.yaml','nav2_params.scan.yaml','planner.yaml'):
 (RECEIPTS/name).write_text(capture.read(name))
lines=capture.read('nav2.log').splitlines();index=next(i for i,s in enumerate(lines) if 'terminate called without an active exception' in s)
(OUT/'controller_abort_context.txt').write_text('\n'.join(lines[max(0,index-35):index+5])+'\n')
(OUT/'pct_runtime_context.txt').write_text('\n'.join(s for s in lines if 'pct_' in s.lower() or 'PCT' in s)+'\n')
work=REMOTE/'blocked_feedback_v230';receipt=json.loads((work/'physics_receipt_v231.json').read_text())
for name,expected in receipt['source_inventory'].items():assert sha(work/name)==expected,name
for name,expected in receipt['installed_files'].items():assert sha(work/name)==expected,name
for name,expected in json.loads((VERSIONS/'v231/manifest.json').read_text())['source_files'].items():assert sha(VERSIONS/'v231'/name)==expected,name
save(RECEIPTS/'post_run_source_parity.json',{'passed':True,'composed_source_files':len(receipt['source_inventory']),'installed_files':len(receipt['installed_files']),'v231_frozen_files_verified':True,'physics_receipt_sha256':sha(work/'physics_receipt_v231.json')})
reports={}
for v in ('v219','v231'):
 raw=REMOTE/'trials'/(v+'_linux_full_attempt01')/'runs'/(v+'_linux_full_attempt01');c=Capture(raw);log=c.read('nav2.log')
 class Log:
  def read_text(self):return log
 starts,done=core.parse_rounds(Log());part=[r for r in done if 45<=r['ros_s']<46.686]
 rows=[r for r in csv.DictReader((HERE/'work'/(v+'_linux_full_attempt01_margins.csv')).open()) if 45<=float(r['time_s'])<46.686]
 known=[float(r['extra_edge_margin_m']) for r in rows if int(r['floor_known'])]
 reports[v]={'completed_rounds':len(part),'successful_rounds':sum(r['success'] for r in part),'incomplete_starts':sum(45<=r['ros_s']<46.686 and not r['completed'] for r in starts),
 'body_samples':len(rows),'known_floor_samples':len(known),'minimum_extra_edge_margin_m':min(known) if known else None,'p05_extra_edge_margin_m':float(np.quantile(known,.05)) if known else None,
 'negative_margin_samples':sum(x<0 for x in known),'target_capped_samples':sum(x>=.15-1e-10 for x in known)}
save(OUT/'common_active_prefix.json',{'window_physics_s':[45,46.686],'definition':'Identical time prefix before the last reactive observation preceding controller abort; no equal-progress or causal ablation claim.',**reports})
save(OUT/'closeout_inputs.json',{'collector_sha256':sha(Path(__file__)),'source_parity':True,'raw_root':str(RAW),'raw_archive_sha256':sha(RAW/'raw_capture.zip'),'collected_files':{str(p.relative_to(OUT)):sha(p) for p in RECEIPTS.rglob('*') if p.is_file()}})
print(json.dumps(reports,indent=2))
