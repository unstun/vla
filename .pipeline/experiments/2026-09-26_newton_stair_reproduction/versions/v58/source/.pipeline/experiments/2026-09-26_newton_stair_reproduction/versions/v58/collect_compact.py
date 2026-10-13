"""Write a bounded allowlist for compact component/trial evidence; bulk stays remote."""
from pathlib import Path
import hashlib,json,argparse
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];ROOT=BASE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['component','trial'],required=True);a=p.parse_args()
files=[]
if a.phase=='component':
 for directory in ['build_evidence','build_evidence_retry02','tests/attempt01','tests/attempt02','paired/attempt01','paired/attempt02']:
  for name in ['result.json','request.json','source_identity.json','remote_artifacts.json','return_manifest.json','build_result.json','build_request.json','source_sha256.json','install_sha256.json']:
   f=HERE/directory/name
   if f.exists():files.append(f)
 native=BASE/'runtime/scan79_goal_endpoint_evidence_v58'
 files.extend(native/n for n in ['source_sha256.json','install_sha256.json','build_result.json'])
else:
 for p in (HERE/'analysis').iterdir():
  if p.suffix in ['.json','.csv'] and not p.name.endswith('_rounds.json') and 'manifest' not in p.name and 'files' not in p.name:files.append(p)
 for n in ['result.json','request.json','preflight.json','remote_artifact_manifest.json']:
  p=HERE/'trials/attempt01'/n
  if p.exists():files.append(p)
records={str(p.relative_to(ROOT)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(set(files))}
assert sum(x['bytes'] for x in records.values())<5*1024**2
name=a.phase+'_return_manifest.json';(HERE/name).write_text(json.dumps(records,indent=2)+'\n')
(HERE/(a.phase+'_return_files.txt')).write_text('\n'.join([*records,str((HERE/name).relative_to(ROOT))])+'\n')
print(json.dumps({'files':len(records),'bytes':sum(x['bytes'] for x in records.values())}))
