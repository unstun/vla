"""Source/build/subset gate for an explicitly authorized Mac physics trial."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
ROOT=BASE.parents[2]
NATIVE=BASE/'runtime/scan82_optimizer_failure_v63'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_receipt(receipt, manifest):
    if not receipt.get('passed') or not receipt.get('source_unchanged'):
        raise ValueError('Mac native build did not pass')
    if receipt.get('image')!='sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb':
        raise ValueError('Mac ROS image differs from pinned image')
    if receipt.get('native_source_sha256')!=manifest['native_source_sha256']:
        raise ValueError('Mac build source differs from frozen v63')
    if not receipt.get('native_install_sha256'):
        raise ValueError('Mac build has no installed byte identity')


def verify(build, manifest):
    if build.resolve()!=NATIVE.resolve():
        raise ValueError('v68 requires the unchanged v63 native source')
    receipt_path=Path(os.environ['V68_BUILD_EVIDENCE'])/'build_receipt.json'
    receipt=json.loads(receipt_path.read_text())
    validate_receipt(receipt,manifest)
    if sha(receipt_path)!=manifest['mac_build_receipt_sha256']:
        raise ValueError('Mac build receipt changed after integration freeze')
    expected=manifest['native_source_sha256']
    if not all(sha(build/name)==h for name,h in expected.items()):
        raise ValueError('Frozen native source changed')
    subset=BASE/'versions/v63/component_qualification.json'
    if sha(subset)!=manifest['mac_subset_qualification_sha256']:
        raise ValueError('Mac subset qualification changed')
    qualification=json.loads(subset.read_text())
    result=BASE/'versions/v63/mac_tests/attempt03/result.json'
    if (not qualification['mac_suite_passed'] or not qualification['build_passed'] or
        qualification['result_sha256']!=sha(result) or not json.loads(result.read_text())['passed']):
        raise ValueError('Required actual Mac native/recorded tests did not pass')
    script="""from pathlib import Path
import hashlib,json,sys
receipt=json.loads(Path(sys.argv[1]).read_text())
root=Path('/workspace')
for group in ('native_source_sha256','native_install_sha256'):
 for name,h in receipt[group].items():
  assert hashlib.sha256((root/name).read_bytes()).hexdigest()==h,name
print('V68_ACTUAL_SOURCE_INSTALL_GATE_PASS')
"""
    checked=subprocess.run(['docker','exec',os.environ['V68_NATIVE_CONTAINER'],
        'python3','-c',script,str(receipt_path)],capture_output=True,text=True,timeout=30)
    checked.check_returncode()
    if 'V68_ACTUAL_SOURCE_INSTALL_GATE_PASS' not in checked.stdout:
        raise ValueError('Actual installed byte gate has no success evidence')
    return {'actual_native_source_install_gate_passed':True,
        'mac_component_subset_passed':True,'full_component_qualification':False,
        'physics_acceptance':False,'receipt_sha256':sha(receipt_path)}
