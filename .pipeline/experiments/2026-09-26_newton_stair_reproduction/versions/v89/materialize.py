"""Compose immutable v87 parents and task-owned v89 overrides into an execution copy."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parents[1]
ROOT = EXPERIMENT.parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    subprocess.run([sys.executable, str(EXPERIMENT/'versions/v86/freeze_sources.py'), 'verify', 'v87'], check=True)
    destination = args.destination.resolve()
    if destination.exists(): raise ValueError('Execution destination must be new')
    source = destination/'src'
    shutil.copytree(EXPERIMENT/'runtime/scan_nav2_foxy_v86/src', source,
                    ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(EXPERIMENT/'versions/v86/nav2_controller', source/'nav2_controller')
    shutil.copytree(EXPERIMENT/'versions/v87/plan_env', source/'plan_env', dirs_exist_ok=True)
    inherited = source/'lite3_nav2_bridge/inherited'
    sources = EXPERIMENT/'runtime_sources'
    identities = {}
    for package, parent in [('backend_adapter', 'backend_adapter'), ('p2b_backend_ros', 'backend_ros')]:
        origin = sources/parent/package
        shutil.copytree(origin, inherited/package, ignore=shutil.ignore_patterns('__pycache__'))
        for path in origin.rglob('*.py'):
            identities[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    shutil.copytree(sources/'navigation_service', inherited/'navigation_service',
                    ignore=shutil.ignore_patterns('__pycache__'))
    for path in (sources/'navigation_service').glob('*.py'):
        identities[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for package in (HERE/'src').iterdir():
        shutil.copytree(package, source/package.name, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__'))
    manifest = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in source.rglob('*') if p.is_file()}
    (destination/'input_identity.json').write_text(json.dumps({'sources': manifest, 'inherited_python': identities}, indent=2)+'\n')


if __name__ == '__main__': main()
