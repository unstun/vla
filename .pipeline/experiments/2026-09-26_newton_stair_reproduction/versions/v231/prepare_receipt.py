"""Bind the existing v230 tested workspace to an immutable physical-run receipt."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
work=Path('/data/sun/vla_mppi_20261009/blocked_feedback_v230')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inventory=json.loads((work/'source_inventory.json').read_text())
for rel,expected in inventory.items():assert sha(work/rel)==expected,rel
count=0
for p in (work/'evidence/attempt04/test_results').rglob('*.xml'):
 t=ET.parse(p).getroot();count+=len(t.findall('.//testcase'))
 for suite in t.iter('testsuite'):
  assert not any(int(suite.attrib.get(k,0)) for k in ('errors','failures','skipped','disabled')),p
assert count==154,count
assert 'Summary: 174 tests, 0 errors, 0 failures, 0 skipped' in (work/'evidence/attempt04/test-result.log').read_text()
installed={str(p.relative_to(work)):sha(p) for p in (work/'install').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
receipt={'passed':True,'unique_cases':count,'colcon_records':174,'source_inventory':inventory,'installed_files':installed,'test_result_sha256':sha(work/'evidence/attempt04/test-result.log'),'navigation_version':'v230','physics_steps':0}
p=work/'physics_receipt_v231.json'
if p.exists():assert json.loads(p.read_text())==receipt,'Existing run receipt differs'
else:p.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'source_files':len(inventory),'installed_files':len(installed),'test_cases':count,'receipt_sha256':sha(p)}))
