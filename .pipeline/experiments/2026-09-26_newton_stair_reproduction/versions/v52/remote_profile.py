"""Bounded same-input parent-path/candidate profiling on the execution copy."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time,shutil
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];ROOT=BASE.parents[2]
NATIVE=BASE/'runtime/scan74_terrain_lookup_v52'
IMAGE='sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--attempt',type=int,default=1);a=parser.parse_args();assert str(ROOT)=='/home/sun/vla_exec/vla'
 out=HERE/f'profiles/attempt{a.attempt:02d}';out.mkdir(parents=True)
 expected=json.loads((NATIVE/'source_sha256.json').read_text());assert all(sha(NATIVE/n)==h for n,h in expected.items())
 sources={str(p.relative_to(ROOT)):sha(p) for p in (HERE/'profiling').iterdir() if p.is_file()}
 for p in (HERE/'profiling').iterdir():
  if p.is_file():shutil.copyfile(p,out/('executed_'+p.name))
 shutil.copyfile(__file__,out/'executed_remote_profile.py')
 name=f'vla-v52-profile-{a.attempt}'
 command=['docker','run','--rm','--pull=never','--platform=linux/amd64','--network=none','--name',name,'--cpus=3','--memory=6g','-e','ROS_DOMAIN_ID=219','-e','ROS_LOCALHOST_ONLY=1','-e','OPENBLAS_NUM_THREADS=1','-e','OMP_NUM_THREADS=1','-v',str(NATIVE)+':/workspace:ro','-v',str(BASE)+':/archive:ro','-v',str(HERE)+':/version:ro','-v',str(HERE/'profiling')+':/profile:ro','-v',str(out)+':/attempt:rw','--entrypoint','/bin/bash',IMAGE,'/profile/inside.sh']
 (out/'request.json').write_text(json.dumps({'command':command,'wall_deadline_s':900,'source_files':sources,'native_source_sha256':expected,'scope':'Offline paired replay; no robot physics or solver timeout policy.'},indent=2)+'\n')
 started=time.monotonic();code=127;error=None
 try:
  with (out/'execution.log').open('w') as f:code=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,timeout=900).returncode
 except (OSError,subprocess.TimeoutExpired) as e:error=repr(e)
 finally:subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=20)
 log=(out/'replay.log').read_text() if (out/'replay.log').exists() else ''
 pairs=[json.loads(x) for x in (out/'tail_pairs.jsonl').read_text().splitlines()] if (out/'tail_pairs.jsonl').exists() else []
 result={'exit_code':code,'error':error,'wall_s':time.monotonic()-started,'paired_replay_passed':code==0 and 'V52_TERRAIN_REPLAY_PASSED' in log and len(pairs)==18 and all(x['same_geometry'] for x in pairs),'pairs':pairs,'source_unchanged':all(sha(ROOT/n)==h for n,h in sources.items()) and all(sha(NATIVE/n)==h for n,h in expected.items())}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 records={str(p.relative_to(ROOT)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in out.rglob('*') if p.is_file() and not p.is_symlink() and 'probe_build' not in p.parts}
 (out/'return_manifest.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='pairs'},indent=2),flush=True)
 raise SystemExit(0 if result['paired_replay_passed'] and result['source_unchanged'] else 1)
if __name__=='__main__':main()
