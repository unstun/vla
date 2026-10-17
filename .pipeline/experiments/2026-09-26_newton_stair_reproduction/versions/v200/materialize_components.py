"""Compose a fresh component workspace from verified v196 + v198 + v200 sources."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--underlay', type=Path, required=True,
                        help='Restored recovery_v196 directory containing src and install')
    parser.add_argument('--workspace', type=Path, required=True,
                        help='New, empty component build directory')
    args = parser.parse_args()
    version = Path(__file__).resolve().parent
    baseline = json.loads((version.parent / 'v196/native_sources.json').read_text())
    for relative, entry in baseline['expected_files'].items():
        expected = entry['sha256'] if isinstance(entry, dict) else entry
        if digest(args.underlay / relative) != expected:
            raise ValueError('Baseline source mismatch: ' + relative)
    for name in ('v198', 'v199', 'v200'):
        root = version.parent / name
        manifest = json.loads((root / 'manifest.json').read_text())
        for relative, expected in manifest['source_files'].items():
            if digest(root / relative) != expected:
                raise ValueError('Frozen source mismatch: ' + str(root / relative))
    args.workspace.mkdir(exist_ok=True, parents=True)
    if any(args.workspace.iterdir()):
        raise ValueError('Workspace must be empty; previous builds are preserved')
    shutil.copytree(args.underlay / 'src', args.workspace / 'src')
    replacements = {'lite3_nav2_interfaces': version.parent / 'v198/src/lite3_nav2_interfaces'}
    replacements.update({name: version / 'src' / name for name in
                         ('scan_nav2_controller', 'nav2_controller', 'lite3_nav2_bridge')})
    for name, source in replacements.items():
        target = args.workspace / 'src' / name
        # Only replace the just-created copy, never the frozen input.
        shutil.rmtree(target)
        shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    inventory = {str(p.relative_to(args.workspace)): digest(p)
                 for p in (args.workspace / 'src').rglob('*') if p.is_file()}
    (args.workspace / 'source_inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
    print(json.dumps({'workspace': str(args.workspace), 'source_files': len(inventory)}))


if __name__ == '__main__':
    main()
