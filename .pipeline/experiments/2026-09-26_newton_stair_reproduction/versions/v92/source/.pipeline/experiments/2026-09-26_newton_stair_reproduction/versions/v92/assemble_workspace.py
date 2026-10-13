"""Create a verified, portable source workspace; does not install or actuate."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
EXPERIMENT=HERE.parents[1]
ROOT=EXPERIMENT.parents[2]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('destination',type=Path);args=parser.parse_args()
    subprocess.run([sys.executable,str(HERE.parent/'v88/freeze_sources.py'),'verify','v92'],check=True)
    destination=args.destination.resolve()
    subprocess.run([sys.executable,str(HERE.parent/'v89/materialize.py'),str(destination)],check=True)
    (destination/'input_identity.json').rename(destination/'v89_parent_materialization.json')
    for package in (HERE/'src').iterdir():
        shutil.copytree(package,destination/'src'/package.name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
    pct=ROOT/'references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_global'
    shutil.copytree(pct/'src/pct/pct_planner',destination/'src/pct_planner')
    dependencies=ROOT/'references/upstream/2026-10-08_nav2_pct_foxy'
    shutil.copytree(dependencies,destination/'third_party')
    shutil.copytree(pct/'LICENSES',destination/'licenses/PCT')
    for name in ('LICENSE','NOTICE','README.md'):
        shutil.copyfile(pct/'src/pct'/name,destination/'licenses/PCT'/name)
    nav2=ROOT/'references/upstream/2026-10-08_nav2_foxy_plugin'
    (destination/'licenses/Nav2').mkdir(parents=True)
    shutil.copyfile(nav2/'LICENSE',destination/'licenses/Nav2/LICENSE')
    shutil.copyfile(HERE/'building_planner.yaml',destination/'native_planner.yaml')
    files={str(p.relative_to(destination)):hashlib.sha256(p.read_bytes()).hexdigest()
           for p in destination.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    (destination/'source_identity.json').write_text(json.dumps({'version':'v92',
        'version_manifest_sha256':hashlib.sha256((HERE/'manifest.json').read_bytes()).hexdigest(),
        'files':files,'hardware_actuation':False},indent=2)+'\n')
    print(json.dumps({'workspace':str(destination),'files':len(files),'source_verified':True}))


if __name__=='__main__':main()
