"""Close every attempt, including failures, with local-returnable evidence."""
from pathlib import Path
import argparse,json,hashlib,importlib.util
from analyze_remote import analyze,Capture
from verify_full_route import verify
from run_remote_full import TASK,BASE
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--attempt',type=int,required=True);a=p.parse_args()
 tag=f'v173_full_candidate_attempt{a.attempt:02d}'
 trial=TASK/'trials'/tag;r=trial/'runs'/tag;out=TASK/'results/v173_full_repeats'/tag;out.mkdir(parents=True,exist_ok=False)
 execution=json.loads((trial/'evidence/execution.json').read_text())
 (out/'execution.json').write_text(json.dumps(execution,indent=2)+'\n')
 try:
  analyze(r,out,True)
  try:route=verify(r)
  except Exception as e:route={'passed':False,'error':repr(e),'run':tag}
  (out/'full_route_verification.json').write_text(json.dumps(route,indent=2)+'\n')
  path=BASE/'audits/2026-10-10_nav2_recovery/analyze_recovery_proofs.py'
  spec=importlib.util.spec_from_file_location('stop_audit',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  proof=mod.analyze(tag);(out/'recovery_proofs.json').write_text(json.dumps(proof,indent=2)+'\n')
  outcome={'closed':True,'run':tag,'arrived':route['passed'],'replacement_owners':proof['replacement_owners'],'all_replacements_have_recorded_proof':proof['all_replacements_have_recorded_proof'],'full_qualification':route['passed'] and proof['all_replacements_have_recorded_proof']}
 except Exception as e:outcome={'closed':True,'run':tag,'full_qualification':False,'analysis_error':repr(e)}
 files={str(f.relative_to(trial)):({'symlink':str(f.readlink())} if f.is_symlink() else {'bytes':f.stat().st_size,'sha256':sha(f)}) for f in trial.rglob('*') if f.is_file() or f.is_symlink()}
 (out/'remote_artifacts.json').write_text(json.dumps({'root':str(trial),'files':files},indent=2)+'\n')
 outcome['files']=len(files);(out/'outcome.json').write_text(json.dumps(outcome,indent=2)+'\n');print(json.dumps(outcome),flush=True)
if __name__=='__main__':main()
