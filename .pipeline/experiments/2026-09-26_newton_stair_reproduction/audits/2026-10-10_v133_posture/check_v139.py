"""Qualify the exact recorded-case feedback repair before physical pilots."""
from pathlib import Path
import hashlib,json,subprocess,sys
TASK=Path('/data/sun/vla_mppi_20261009');BASE=Path(__file__).resolve().parents[2];V=BASE/'versions/v139';OUT=TASK/'results/recovery_v139_02'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 root=TASK/'results/sampled_rebound_contract'
 old=json.loads((root/'v137_02/result.json').read_text());new=json.loads((root/'v139_02/result.json').read_text())
 assert old['passed'] and new['passed'] and old['map_digest']==new['map_digest']
 assert old['input_identity_sha256']==new['input_identity_sha256'] and old['seed_sha256']==new['seed_sha256']
 assert 'SAMPLED_REBOUND_CASE accepted=0' in old['cases'] and 'SAMPLED_REBOUND_CASE accepted=1' in new['cases']
 assert 'SAMPLED_REBOUND_HINT_CHECKS 7 passed' in new['cases']
 for script,log in [('test_host_port.py','host_tests02.log'),('test_output_ownership.py','ownership02.log'),('test_native_graph.py','native_graph_final02.log')]:
  with (OUT/log).open('w') as f:subprocess.run([sys.executable,str(V/script)],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=120)
 build=(OUT/'build.log').read_text();assert '14 packages finished' in build and '38 tests, 0 errors, 0 failures' in build
 checks={'old_failure':root/'v137_02/result.json','new_repair':root/'v139_02/result.json','host':OUT/'host_tests02.log','ownership':OUT/'ownership02.log','graph':OUT/'native_graph_preflight_final.json','build':OUT/'build.log'}
 q={'passed':True,'native_packages_available':14,'native_component_tests':38,'repair_hint_checks':7,'native_variants':{'baseline':'v137','candidate':'v139'},'runtime_receipts':{k:sha(OUT/(k+'_receipt.json')) for k in ['baseline','candidate']},'source_audit_sha256':sha(V/'source_audit.json'),'checks':{k:{'path':str(p),'sha256':sha(p)} for k,p in checks.items()},'scope':'Actual recorded map/boundary old rejection and new full-curve acceptance. No physical repeatability claim yet.','full_navigation_accepted':False}
 (V/'quality.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({'passed':True,'native_tests':38,'hint_checks':7,'captured_failure_repaired':True}))
if __name__=='__main__':main()
