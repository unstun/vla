"""Freeze source/config snapshots for the Foxy navigation version chain."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

VERSIONS=Path(__file__).resolve().parent.parent
EXPERIMENT=VERSIONS.parent
ROOT=EXPERIMENT.parents[2]
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def selected(version):
    directory=VERSIONS/version
    suffixes={'.py','.cpp','.h','.hpp','.sh','.yaml','.xml'}
    configs={'CMakeLists.txt','corner_scenario.json','navigation_contract.json',
             'physical_floor_input.json','upstream_sources.json'}
    paths=[p for p in directory.iterdir() if p.is_file() and (p.suffix in suffixes or p.name in configs)]
    if (directory/'src').exists():
        paths.extend(p for p in (directory/'src').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    if version=='v89':
        for name in ('backend_adapter/backend_adapter','backend_ros/p2b_backend_ros','navigation_service'):
            paths.extend((EXPERIMENT/'runtime_sources'/name).rglob('*.py'))
    if version=='v90':
        for name in ('references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_global',
                     'references/upstream/2026-10-08_nav2_pct_foxy'):
            paths.extend(p for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    return sorted(set(p for p in paths if '__pycache__' not in p.parts))


def verify(version):
    directory=VERSIONS/version
    manifest=json.loads((directory/'manifest.json').read_text())
    for name,value in manifest['source_files'].items():
        if SHA(ROOT/name)!=value or SHA(ROOT/manifest['snapshot_locations'][name])!=value:
            raise ValueError('Source or snapshot changed: '+name)
    if SHA(VERSIONS/manifest['parent']/'manifest.json')!=manifest['parent_manifest_sha256']:
        raise ValueError('Parent manifest changed')
    if SHA(directory/'quality.json')!=manifest['quality_sha256']:
        raise ValueError('Qualification record changed')
    print(json.dumps({'version':version,'verified_pairs':len(manifest['source_files']),'passed':True}))


def freeze(version):
    directory=VERSIONS/version
    if (directory/'manifest.json').exists(): raise ValueError('Never overwrite a frozen version')
    parent='v'+str(int(version[1:])-1)
    previous=json.loads((VERSIONS/parent/'manifest.json').read_text())
    files=dict(previous['source_files']);locations=dict(previous['snapshot_locations'])
    for path in selected(version):
        relative=str(path.relative_to(ROOT))
        digest=SHA(path)
        if files.get(relative)==digest:continue
        snapshot=directory/'source'/relative
        snapshot.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,snapshot)
        files[relative]=digest;locations[relative]=str(snapshot.relative_to(ROOT))
    manifest={'version':version,'parent':parent,'parent_manifest_sha256':SHA(VERSIONS/parent/'manifest.json'),
        'status':'frozen_component_checked_navigation_not_accepted','platform':'Ubuntu 20.04 / ROS 2 Foxy / ARM64',
        'nav2_commit':'a947ab5656e46ae3aa1afdf95e1706a16e478974',
        'source_files':files,'snapshot_locations':locations,'quality_sha256':SHA(directory/'quality.json')}
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    verify(version)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['freeze','verify'])
    parser.add_argument('version');args=parser.parse_args()
    if not args.version.startswith('v') or not args.version[1:].isdigit() or int(args.version[1:])<88:
        raise ValueError('Expected v88 or a later integer version')
    (freeze if args.action=='freeze' else verify)(args.version)
