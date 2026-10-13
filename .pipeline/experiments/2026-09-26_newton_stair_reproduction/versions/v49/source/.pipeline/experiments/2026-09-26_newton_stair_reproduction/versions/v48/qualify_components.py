from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
NATIVE=BASE/'runtime/scan71_remaining_curve_v48'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 r=json.loads((HERE/'tests/attempt02/result.json').read_text())
 assert r['exit_code']==0 and r['native_passed'] and r['cache_passed'] and r['warm_passed'] and r['source_unchanged'] and r['cleanup_confirmed']
 assert all(p['geometry_exact_parent'] for p in r['plans'])
 assert all(p['warm_accepts']==3 and len(p['paired_timings'])==6 for p in r['warm_fixtures'].values())
 for name in ['source_sha256.json','install_sha256.json']:
  rows=json.loads((NATIVE/name).read_text());assert all(sha(NATIVE/p)==d for p,d in rows.items())
 assert json.loads((NATIVE/'build_result.json').read_text())['passed']
 q={'cache_geometry_and_contract_passed':True,'warm_contract_passed':True,'native_checks':r['native_checks'],'cache_checks':r['cache_checks'],'warm_fixtures':r['warm_fixtures'],'component_result_sha256':sha(HERE/'tests/attempt02/result.json'),'native_install_verified_files':len(json.loads((NATIVE/'install_sha256.json').read_text())),'cpu_graph_exact_continuous_trace':True,'controller_configuration_hz':30,'global_configuration_hz':1,'full_stack_validated':False,'full_scene_30hz_validated':False,'scope':'Two native stopped-state cold/warm paired fixtures, not the complete live retry distribution.'}
 (HERE/'component_qualification.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q,indent=2))
if __name__=='__main__':main()
