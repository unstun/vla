"""Bind the tested ARM64 rebuild; run inside its actual execution image."""
from pathlib import Path
import argparse
import hashlib
import json
import platform


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image-id', required=True)
    args = parser.parse_args()
    assert platform.machine() == 'aarch64'
    task = Path('/task')
    workspace = task / 'recovery_v147'
    log = (task / 'evidence/native_build.log').read_text()
    assert '14 packages finished' in log and '0 errors, 0 failures' in log
    source = json.loads((workspace / 'source_identity.json').read_text())
    for name, digest in source['files'].items():
        assert sha(workspace / name) == digest, name
    files = {str(p): sha(p) for directory in ('src', 'install', 'dependencies/osqp-install')
             for p in (workspace / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for name in ['recovery_v147/source_identity.json', 'global_coverage_v135_foxy/map.pickle',
                 'support_coverage_v134/partial.txt', 'evidence/packages.tsv', 'evidence/foxy_python.txt']:
        files[str(task / name)] = sha(task / name)
    receipt = {'passed': True, 'platform': 'linux/arm64', 'ros_distro': 'foxy',
               'variant': 'candidate', 'native_version': 'v147', 'image_id': args.image_id,
               'files': files, 'source_identity_sha256': sha(workspace / 'source_identity.json'),
               'test_log_sha256': sha(task / 'evidence/native_build.log')}
    path = task / 'evidence/native_receipt.json'
    path.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'passed': True, 'receipt_sha256': sha(path), 'files': len(files)}))


if __name__ == '__main__':
    main()
