"""Compose v204 plus the v206 command-continuity overlay."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--underlay', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    version = Path(__file__).resolve().parent
    manifest = json.loads((version / 'manifest.json').read_text())
    for relative, expected in manifest['source_files'].items():
        if hashlib.sha256((version / relative).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen source mismatch: ' + relative)
    subprocess.run([sys.executable, str(version.parent / 'v204/materialize_components.py'),
                    '--underlay', str(args.underlay), '--workspace', str(args.workspace)], check=True)
    for package in (version / 'src').iterdir():
        target = args.workspace / 'src' / package.name
        if target.exists():
            shutil.rmtree(target)  # Only the fresh copy, never the old underlay.
        shutil.copytree(package, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    inventory = {str(p.relative_to(args.workspace)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in (args.workspace / 'src').rglob('*') if p.is_file()}
    (args.workspace / 'source_inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
    print(json.dumps({'version': 'v206', 'composed_source_files': len(inventory)}))


if __name__ == '__main__':
    main()
