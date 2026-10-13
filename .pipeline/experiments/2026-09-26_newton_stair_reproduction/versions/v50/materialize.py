"""Materialize the direct v48 native parent plus the reviewed v50 patch."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
PARENT=BASE/'runtime/scan71_remaining_curve_v48'
DEFAULT=BASE/'runtime/scan73_v48_continuity_v50'
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=DEFAULT);args=parser.parse_args()
 assert args.output.resolve()!=PARENT.resolve()
 assert not (HERE/'manifest.json').exists() or args.output.resolve()!=DEFAULT.resolve(),'Never overwrite a frozen runtime'
 expected_parent=json.loads((HERE/'parent_identity.json').read_text())['native_source_sha256']
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 assert all(sha(PARENT/name)==digest for name,digest in expected_parent.items())
 assert not args.output.exists(),'Use a new destination; preserve prior candidates'
 shutil.copytree(PARENT/'src',args.output/'src')
 patch=HERE/'changes.patch'
 if patch.stat().st_size:
  subprocess.run(['patch','-p5','--forward','--input',str(patch.resolve())],cwd=args.output,check=True)
 expected=json.loads((DEFAULT/'source_sha256.json').read_text())
 actual={str(p.relative_to(args.output)):sha(p) for p in (args.output/'src').rglob('*') if p.is_file()}
 assert actual==expected
 (args.output/'source_sha256.json').write_text(json.dumps(expected,indent=2)+'\n')
 print('Exact v50 prepared source reproduced from v48:',len(expected))
if __name__=='__main__':main()
