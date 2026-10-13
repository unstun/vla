"""Reproduce v52 native source from frozen v50; never overwrite a runtime."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
PARENT = BASE/'runtime/scan73_v48_continuity_v50'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    preparation=json.loads((HERE/'preparation.json').read_text())
    frozen=json.loads((BASE/'versions/v50/manifest.json').read_text())
    assert sha(BASE/'versions/v50/manifest.json')==preparation['parent_manifest_sha256']
    assert all(sha(PARENT/n)==h for n,h in frozen['native_source_sha256'].items())
    assert not args.output.exists(),'Use a new output directory'
    shutil.copytree(PARENT/'src',args.output/'src')
    # Only the two changed text files were normalized to LF in this candidate.
    for name in preparation['changed_native_files']:
        path=args.output/name
        path.write_text(path.read_text())
    subprocess.run(['patch','-p1','--forward','--input',str((HERE/'changes.patch').resolve())],cwd=args.output,check=True)
    actual={str(p.relative_to(args.output)):sha(p) for p in (args.output/'src').rglob('*') if p.is_file()}
    assert actual==preparation['source_sha256'],'Materialized source identity differs'
    (args.output/'source_sha256.json').write_text(json.dumps(actual,indent=2)+'\n')
    print(json.dumps({'version':'v52','native_source_files':len(actual),'exact_parent_patch_reproduction':True}))
if __name__=='__main__':main()
