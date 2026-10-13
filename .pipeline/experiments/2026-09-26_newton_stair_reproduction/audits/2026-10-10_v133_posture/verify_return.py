"""Verify every returned compact byte and frozen local identity."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
H=Path(__file__).resolve().parent;B=H.parents[1]
def sha(p):
 d=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):d.update(b)
 return d.hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument('--bundle',type=Path,required=True);args=a.parse_args();root=args.bundle.resolve();m=json.loads((root/'MANIFEST.json').read_text())
 for n,e in m['files'].items():
  p=root/n;assert p.is_relative_to(root) and p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],n
 assert len(m['raw_trials'])==30 and all(r['verified'] for r in m['raw_trials'])
 assert m['original_failed_trial_reverified']['run']=='v133_candidate_attempt02'
 identities={}
 for v in ['v134','v135','v136','v137','v138','v139']:
  identities[v]=json.loads(subprocess.check_output([sys.executable,str(B/'versions'/v/'freeze_host.py'),'verify'],text=True))
 summary=json.loads((root/'results/v133_posture/final_analysis01/summary.json').read_text());assert summary['groups']['candidate']['runs']==6
 # Audit the frozen qualification hashes against actual returned evidence.
 for v in identities:
  q=json.loads((B/'versions'/v/'quality.json').read_text())
  for d in q['checks'].values():assert sha(root/Path(d['path']).relative_to('/data/sun/vla_mppi_20261009'))==d['sha256'],d['path']
 proof=json.loads((root/'results/v133_posture/final_analysis01/stop_proofs.json').read_text());assert len(proof['runs'])==30
 result={'passed':True,'returned_files':len(m['files']),'returned_bytes':sum(e['bytes'] for e in m['files'].values()),'raw_new_trials_verified_remotely':len(m['raw_trials']),'raw_new_trial_bytes':sum(e['bytes'] for e in m['raw_trials']),'bundle_manifest_sha256':sha(root/'MANIFEST.json'),'bundle':str(root),'source_identities':identities,'fresh_comparison':summary['groups'],'scenario_candidate_gate_passed':summary['candidate_gate_passed'],'all_candidate_replacement_proofs_passed':summary['all_candidate_replacement_proofs_passed'],'candidate_replacements':summary['candidate_replacements'],'verification_script_sha256':sha(Path(__file__))}
 out=H/'final_verification.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
