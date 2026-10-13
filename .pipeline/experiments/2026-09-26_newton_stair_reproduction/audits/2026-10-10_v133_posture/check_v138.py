"""Validate installed native footprint queries and qualify the candidate host."""
from pathlib import Path
import csv,hashlib,json,subprocess,sys
TASK=Path('/data/sun/vla_mppi_20261009');BASE=Path(__file__).resolve().parents[2];V=BASE/'versions/v138';OUT=TASK/'results/recovery_v138'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 root=TASK/'results/body_envelope_contract'
 rows=[]
 for ver in ['v137','v138']:
  result=json.loads((root/ver/'result.json').read_text());assert result['passed']
  with (root/ver/'queries.csv').open() as f: rows.append(list(csv.reader(f)))
 old,new=rows;assert len(old)==len(new)==6800
 for a,b in zip(old,new):assert a[:3]==b[:3] and int(b[3])>=int(a[3])
 added=sum(a[3]!=b[3] for a,b in zip(old,new));clear=sum(b[3]=='0' for b in new)
 assert added>0 and clear>0
 a=json.loads((root/'v137/result.json').read_text());b=json.loads((root/'v138/result.json').read_text())
 assert a['map_digest']==b['map_digest'] and a['input_identity_sha256']==b['input_identity_sha256']
 (root/'comparison.json').write_text(json.dumps({'passed':True,'queries':6800,'new_rejects':added,'unchanged_clear':clear,'old_rejects_preserved':True,'same_recorded_map':True},indent=2)+'\n')
 for script,log in [('test_host_port.py','host_tests.log'),('test_output_ownership.py','ownership.log'),('test_native_graph.py','native_graph_final.log')]:
  with (OUT/log).open('w') as f:subprocess.run([sys.executable,str(V/script)],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=120)
 build=(OUT/'build.log').read_text();assert '14 packages finished' in build and '0 failures' in build and '0 errors' in build
 checks={'old_envelope':root/'v137/result.json','new_envelope':root/'v138/result.json','envelope_comparison':root/'comparison.json','host':OUT/'host_tests.log','ownership':OUT/'ownership.log','graph':OUT/'native_graph_preflight_final.json','build':OUT/'build.log'}
 quality={'passed':True,'native_packages_available':14,'native_component_tests':38,'native_variants':{'baseline':'v137','candidate':'v138'},'runtime_receipts':{k:sha(OUT/(k+'_receipt.json')) for k in ['baseline','candidate']},'source_audit_sha256':sha(V/'source_audit.json'),'checks':{k:{'path':str(p),'sha256':sha(p)} for k,p in checks.items()},'scope':'Add the same conservative static support envelope to local planning. All original rejects preserved. Full physical navigation remains unaccepted.','full_navigation_accepted':False}
 (V/'quality.json').write_text(json.dumps(quality,indent=2)+'\n');print(json.dumps({'passed':True,'additional_rejects':added,'unchanged_clear':clear}))
if __name__=='__main__':main()
