"""Require the selected same-host source/install receipt; no ARM64 receipt reuse."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def verify(build, manifest):
    if build.resolve() != HERE or sha(HERE/'quality.json') != manifest['quality_sha256']:
        raise ValueError('Wrong source or component quality identity')
    variant = os.environ['V139_VARIANT']
    if variant not in ('baseline', 'candidate'):
        raise ValueError('Unknown comparison variant')
    path = Path(os.environ['V139_BUILD_EVIDENCE'])/'build_receipt.json'
    quality = json.loads((HERE/'quality.json').read_text())
    receipt = json.loads(path.read_text())
    if not quality['passed'] or sha(path) != quality['runtime_receipts'][variant]:
        raise ValueError('Unqualified source/install receipt')
    if not receipt['passed'] or receipt['platform'] != 'linux/amd64' or receipt['variant'] != variant:
        raise ValueError('Wrong execution platform/variant')
    container = os.environ['V139_NATIVE_CONTAINER']
    image = subprocess.check_output(['docker', 'inspect', '--format', '{{.Image}}', container], text=True).strip()
    if image != receipt['image_id']:
        raise ValueError('Image differs from tested image')
    script = '''from pathlib import Path
import hashlib,json,sys
r=json.loads(Path(sys.argv[1]).read_text())
for name,expected in r['files'].items():
 assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected,name
print('V139_NATIVE_IDENTITY_PASS')
'''
    result = subprocess.run(['docker', 'exec', container, 'python3', '-c', script, str(path)],
                            capture_output=True, text=True, check=True, timeout=90)
    if 'V139_NATIVE_IDENTITY_PASS' not in result.stdout:
        raise ValueError('Missing native identity witness')
    return {'passed': True, 'variant': variant, 'receipt_sha256': sha(path), 'physics_acceptance': False}
