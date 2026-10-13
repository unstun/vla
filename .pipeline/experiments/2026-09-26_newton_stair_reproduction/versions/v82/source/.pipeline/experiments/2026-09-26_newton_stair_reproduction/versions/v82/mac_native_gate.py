"""Check new source/install and component evidence before Mac physics."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
NATIVE=BASE/'runtime/scan85_backlog_map_v82'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()


def verify(build,manifest):
    if build.resolve()!=NATIVE.resolve():raise ValueError('Wrong native source for v82')
    expected=manifest['native_source_sha256']
    if not all(sha(build/name)==value for name,value in expected.items()):raise ValueError('Native source changed')
    quality=HERE/'quality.json'
    if sha(quality)!=manifest['quality_sha256'] or not json.loads(quality.read_text())['passed']:
        raise ValueError('Required v82 component qualification missing or changed')
    receipt=Path(os.environ['V82_BUILD_EVIDENCE'])/'build_receipt.json'
    recorded=json.loads(receipt.read_text())
    if not recorded['passed'] or recorded['native_source_sha256']!=expected:
        raise ValueError('Installed build source does not match v82')
    script='''from pathlib import Path
import hashlib,json,sys
receipt=json.loads(Path(sys.argv[1]).read_text())
root=Path('/workspace')
for group in ('native_source_sha256','native_install_sha256'):
 for name,value in receipt[group].items():
  assert hashlib.sha256((root/name).read_bytes()).hexdigest()==value,name
print('V82_SOURCE_INSTALL_GATE_PASS')
'''
    checked=subprocess.run(['docker','exec',os.environ['V82_NATIVE_CONTAINER'],'python3','-c',script,str(receipt)],
                           capture_output=True,text=True,timeout=30,check=True)
    if 'V82_SOURCE_INSTALL_GATE_PASS' not in checked.stdout:raise ValueError('Installed-byte check has no success evidence')
    return {'passed':True,'source_and_install_verified':True,'component_verified':True,
            'receipt_sha256':sha(receipt),'physics_acceptance':False,'steady_30hz_acceptance':False}
