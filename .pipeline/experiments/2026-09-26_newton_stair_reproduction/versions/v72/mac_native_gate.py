"""Gate actual upstream source, executable bytes and native cancel evidence."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
NATIVE=BASE/'runtime/scan83_upstream_probe_v71'
IMAGE='sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_receipt(receipt, manifest):
    if not receipt.get('passed') or not receipt.get('source_unchanged'):
        raise ValueError('Native upstream build did not pass')
    if receipt.get('image')!=IMAGE:
        raise ValueError('Mac ROS image differs from pinned image')
    if receipt.get('native_source_sha256')!=manifest['native_source_sha256']:
        raise ValueError('Built source differs from frozen upstream probe')
    if not receipt.get('native_install_sha256'):
        raise ValueError('Native build has no installed byte identity')


def verify(build, manifest):
    if build.resolve()!=NATIVE.resolve():
        raise ValueError('v72 requires its explicitly selected upstream probe')
    receipt_path=Path(os.environ['V72_BUILD_EVIDENCE'])/'build_receipt.json'
    receipt=json.loads(receipt_path.read_text())
    validate_receipt(receipt,manifest)
    if sha(receipt_path)!=manifest['mac_build_receipt_sha256']:
        raise ValueError('Mac build receipt changed after freeze')
    if not all(sha(build/name)==h for name,h in manifest['native_source_sha256'].items()):
        raise ValueError('Native upstream source changed')
    smoke_path=Path(os.environ['V72_BUILD_EVIDENCE'])/'native_transport_smoke.json'
    if sha(smoke_path)!=manifest['transport_smoke_sha256'] or not json.loads(smoke_path.read_text())['passed']:
        raise ValueError('Native route/cancel transport smoke did not pass')
    script='''from pathlib import Path
import hashlib,json,sys
receipt=json.loads(Path(sys.argv[1]).read_text())
for group in ('native_source_sha256','native_install_sha256'):
 for name,h in receipt[group].items():
  assert hashlib.sha256((Path('/workspace')/name).read_bytes()).hexdigest()==h,name
print('V72_ACTUAL_SOURCE_INSTALL_GATE_PASS')
'''
    checked=subprocess.run(['docker','exec',os.environ['V72_NATIVE_CONTAINER'],
        'python3','-c',script,str(receipt_path)],capture_output=True,text=True,timeout=30)
    checked.check_returncode()
    if 'V72_ACTUAL_SOURCE_INSTALL_GATE_PASS' not in checked.stdout:
        raise ValueError('Installed source gate has no success evidence')
    return {'actual_native_source_install_gate_passed':True,'native_transport_smoke_passed':True,
        'navigation_acceptance':False,'receipt_sha256':sha(receipt_path),
        'claim':'Transport/build qualification only; upstream planning contracts differ from local v63'}
