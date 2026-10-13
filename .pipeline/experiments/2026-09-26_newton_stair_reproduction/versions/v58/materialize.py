"""Reproduce v58 source from its frozen parent in a new output directory."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
PARENT=BASE/'runtime/scan78_physical_floor_presence_v56'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    spec=json.loads((HERE/'preparation.json').read_text());parent=BASE/'versions/v57/manifest.json';frozen=json.loads(parent.read_text())
    assert sha(parent)==spec['parent_manifest_sha256'];assert all(sha(PARENT/n)==h for n,h in frozen['native_source_sha256'].items())
    assert not args.output.exists(),'Output must be new'
    shutil.copytree(PARENT/'src',args.output/'src')
    for name in spec['changed_native_files']:
        p=args.output/name
        if p.exists(): p.write_text(p.read_text())
    subprocess.run(['patch','-p1','--forward','--input',str((HERE/'changes.patch').resolve())],cwd=args.output,check=True)
    actual={str(p.relative_to(args.output)):sha(p) for p in (args.output/'src').rglob('*') if p.is_file()}
    assert actual==spec['source_sha256'],'Materialized bytes differ'
    (args.output/'source_sha256.json').write_text(json.dumps(actual,indent=2)+'\n')
    print(json.dumps({'version':'v58','exact_parent_patch_reproduction':True,'files':len(actual)}))
if __name__=='__main__':main()
