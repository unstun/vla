"""Audit a closed Mac attempt without modifying its archived raw files."""
from pathlib import Path
import argparse,json,importlib.util
from analyze_remote import analyze,Capture
from verify_full_route import verify
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);a=p.parse_args()
 root=a.trial/'runs'/a.trial.name;out=HERE/'results'/a.trial.name;out.mkdir(exist_ok=True)
 try:analyze(root,out,True)
 except Exception as e:
  result={'run':root.name,'full_qualification':False,'analysis_error':repr(e),'claim':'Interrupted run; preserve archived raw evidence'}
  (out/'outcome.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return
 try:route=verify(root)
 except Exception as e:route={'passed':False,'run':root.name,'error':repr(e)}
 (out/'full_route_verification.json').write_text(json.dumps(route,indent=2)+'\n')
 spec=importlib.util.spec_from_file_location('stop_audit',BASE/'audits/2026-10-10_nav2_recovery/analyze_recovery_proofs.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.Capture=lambda ignored:Capture(root)
 proof=m.analyze(root.name);(out/'recovery_proofs.json').write_text(json.dumps(proof,indent=2)+'\n')
 outcome={'run':root.name,'arrived':route['passed'],'replacement_owners':proof['replacement_owners'],'all_replacements_have_recorded_proof':proof['all_replacements_have_recorded_proof'],'full_qualification':route['passed'] and proof['all_replacements_have_recorded_proof']}
 (out/'outcome.json').write_text(json.dumps(outcome,indent=2)+'\n');print(json.dumps(outcome),flush=True)
if __name__=='__main__':main()
