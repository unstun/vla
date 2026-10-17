"""Close every attempt, including failures, with local-returnable evidence."""
from pathlib import Path
import argparse,json,hashlib,importlib.util
from analyze_remote import analyze,Capture
from verify_full_route import verify
from run_remote_full import TASK,BASE
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--attempt',type=int,required=True);a=p.parse_args()
 tag=f'v191_full_candidate_attempt{a.attempt:02d}'
 trial=TASK/'trials'/tag;r=trial/'runs'/tag;out=TASK/'results/v191_full_repeats'/tag;out.mkdir(parents=True,exist_ok=False)
 execution=json.loads((trial/'evidence/execution.json').read_text())
 (out/'execution.json').write_text(json.dumps(execution,indent=2)+'\n')
 try:
  analyze(r,out,True)
  try:route=verify(r)
  except Exception as e:route={'passed':False,'error':repr(e),'run':tag}
  (out/'full_route_verification.json').write_text(json.dumps(route,indent=2)+'\n')
  obs=Capture(r).rows('artifacts/reactive_observations.jsonl')
  routes=sum(row['event']=='pct_route' for row in obs)
  curves=sum(row['event']=='bspline' for row in obs)
  outcome={'closed':True,'run':tag,'arrived':route['passed'],
           'pct_route_publications':routes,'bspline_publications':curves,
           'command_transport':'direct_nav2_twist',
           'full_qualification':route['passed'] and routes>0 and curves>0}
 except Exception as e:outcome={'closed':True,'run':tag,'full_qualification':False,'analysis_error':repr(e)}
 files={str(f.relative_to(trial)):({'symlink':str(f.readlink())} if f.is_symlink() else {'bytes':f.stat().st_size,'sha256':sha(f)}) for f in trial.rglob('*') if f.is_file() or f.is_symlink()}
 (out/'remote_artifacts.json').write_text(json.dumps({'root':str(trial),'files':files},indent=2)+'\n')
 outcome['files']=len(files);(out/'outcome.json').write_text(json.dumps(outcome,indent=2)+'\n');print(json.dumps(outcome),flush=True)
if __name__=='__main__':main()
