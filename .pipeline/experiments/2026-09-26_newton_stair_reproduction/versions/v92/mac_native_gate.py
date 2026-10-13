"""Verify the actual Foxy/PCT/bridge install before the inherited Newton trial."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

HERE=Path(__file__).resolve().parent
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()


def verify(build,manifest):
    if build.resolve()!=HERE.resolve():raise ValueError('Wrong v92 source selection')
    if sha(HERE/'quality.json')!=manifest['quality_sha256']:
        raise ValueError('Component qualification changed')
    if not json.loads((HERE/'quality.json').read_text())['passed']:
        raise ValueError('Component qualification missing')
    receipt=Path(os.environ['V92_BUILD_EVIDENCE'])/'build_receipt.json'
    quality=json.loads((HERE/'quality.json').read_text())
    if sha(receipt)!=quality['runtime_receipt_sha256']:
        raise ValueError('Execution receipt differs from the qualified build')
    expected=json.loads(receipt.read_text())
    if not expected['passed'] or expected['platform']!='linux/arm64' or expected['ros_distro']!='foxy':
        raise ValueError('Wrong execution build')
    actual_image=subprocess.check_output(['docker','inspect','--format','{{.Image}}',
        os.environ['V92_NATIVE_CONTAINER']],text=True).strip()
    if actual_image!=expected['execution_image_sha256']:
        raise ValueError('Execution image differs from the qualified Foxy environment')
    script='''from pathlib import Path
import hashlib,json,sys
receipt=json.loads(Path(sys.argv[1]).read_text())
for name,value in receipt['runtime_file_sha256'].items():
 assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==value,name
print('V92_FOXY_SOURCE_INSTALL_GATE_PASS')
'''
    result=subprocess.run(['docker','exec',os.environ['V92_NATIVE_CONTAINER'],'python3','-c',script,str(receipt)],
                          check=True,capture_output=True,text=True,timeout=45)
    if 'V92_FOXY_SOURCE_INSTALL_GATE_PASS' not in result.stdout:
        raise ValueError('Missing installed identity verification')
    return {'passed':True,'receipt_sha256':sha(receipt),'physics_acceptance':False}
