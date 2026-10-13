"""Export the verified v99 workspace with the v113 native clock scheduling repair."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    subprocess.run([sys.executable, str(HERE.parent/'v88/freeze_sources.py'), 'verify', 'v113'], check=True)
    destination = args.destination.resolve()
    subprocess.run([sys.executable, str(HERE.parent/'v110/assemble_workspace.py'), str(destination)], check=True)
    (destination/'source_identity.json').rename(destination/'v110_parent_source_identity.json')
    for package in (HERE/'src').iterdir():
        shutil.copytree(package, destination/'src'/package.name, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copyfile(HERE/'build_export.sh', destination/'build_export.sh')
    files = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in destination.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    (destination/'source_identity.json').write_text(json.dumps({
        'version': 'v113', 'version_manifest_sha256': hashlib.sha256((HERE/'manifest.json').read_bytes()).hexdigest(),
        'files': files, 'hardware_actuation': False}, indent=2)+'\n')
    print(json.dumps({'workspace': str(destination), 'files': len(files), 'source_verified': True}))


if __name__ == '__main__':
    main()
