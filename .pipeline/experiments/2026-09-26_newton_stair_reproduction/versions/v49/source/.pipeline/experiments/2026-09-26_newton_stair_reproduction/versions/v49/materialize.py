"""Restore the exact v49 source from the verified parent and reviewed patch."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
PARENT=BASE/'runtime/scan71_remaining_curve_v48'
DEFAULT=BASE/'runtime/scan72_solve_budget_v49'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=DEFAULT)
    args=parser.parse_args()
    assert args.output.resolve()!=PARENT.resolve()
    assert not (HERE/'manifest.json').exists() or args.output.resolve()!=DEFAULT.resolve(),'Never overwrite a frozen runtime'
    rows=json.loads((HERE/'parent_identity.json').read_text())['native_source_sha256']
    assert all(hashlib.sha256((PARENT/name).read_bytes()).hexdigest()==d for name,d in rows.items())
    shutil.copytree(PARENT/'src',args.output/'src',dirs_exist_ok=True)
    subprocess.run(['patch','-p5','--forward','--input',str((HERE/'changes.patch').resolve())],cwd=args.output,check=True)
    expected=json.loads((DEFAULT/'source_sha256.json').read_text())
    assert all(hashlib.sha256((args.output/name).read_bytes()).hexdigest()==d for name,d in expected.items())
    (args.output/'source_sha256.json').write_text(json.dumps(expected,indent=2)+'\n')
    print('Exact v49 native source reproduced:',len(expected))


if __name__=='__main__':
    main()
