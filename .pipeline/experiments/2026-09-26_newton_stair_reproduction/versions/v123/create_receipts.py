"""Bind actual x86_64 source, binaries and environment after successful tests."""
from pathlib import Path
import hashlib
import json
import subprocess

TASK = Path('/data/sun/vla_mppi_20261009')
HERE = TASK/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v123'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
log = (TASK/'results/build_native03.log').read_text()
if 'V123_NATIVE_BUILD_TESTS_PASS' not in log:
    raise ValueError('Missing successful native build and tests')
image = (TASK/'results/foxy_image_identity03.txt').read_text().split()[0]
receipts = {}
for variant in ('baseline', 'candidate'):
    workspace = TASK/variant
    tests = (TASK/'results'/f'{variant}-tests.log').read_text()
    if '0 errors, 0 failures, 0 skipped' not in tests:
        raise ValueError('Native test failures: '+variant)
    exported = json.loads((workspace/'source_identity.json').read_text())
    for name, expected in exported['files'].items():
        if sha(workspace/name) != expected:
            raise ValueError('Exported source mutated: '+name)
    files = {str(Path('/task')/variant/p.relative_to(workspace)): sha(p)
             for directory in ('src', 'install', 'dependencies/osqp-install')
             for p in (workspace/directory).rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    files['/task/results/packages.tsv'] = sha(TASK/'results/packages.tsv')
    files['/task/results/foxy_python.txt'] = sha(TASK/'results/foxy_python.txt')
    receipt = {'passed': True, 'platform': 'linux/amd64', 'ros_distro': 'foxy',
               'variant': variant, 'native_version': exported['version'], 'image_id': image,
               'files': files, 'source_identity_sha256': sha(workspace/'source_identity.json'),
               'test_log_sha256': sha(TASK/'results'/f'{variant}-tests.log')}
    path = TASK/'results'/f'{variant}_receipt.json'
    path.write_text(json.dumps(receipt, indent=2)+'\n')
    receipts[variant] = sha(path)
host = json.loads((TASK/'results/host_preflight.json').read_text())
assert host['passed'] and not host['physics_advanced']
quality = {'passed': True, 'native_packages_available': 14,
           'runtime_receipts': receipts, 'host_preflight_sha256': sha(TASK/'results/host_preflight.json'),
           'scope': 'Linux host/component checks only', 'full_navigation_accepted': False}
(TASK/'results/quality.json').write_text(json.dumps(quality, indent=2)+'\n')
print(json.dumps(quality))
