"""Return existing XMLs and receipts; never rerun tests or physics."""
from pathlib import Path
import hashlib,json,shutil,xml.etree.ElementTree as ET
R=Path('/home/ubuntu/sun/vla_v290_20261021')
out=R/'component_return01';out.mkdir(exist_ok=False)
rows=[]
for source in sorted((R/'native/build').glob('*/test_results/**/*.xml')):
    relative=source.relative_to(R/'native/build');p=out/'test_results'/relative
    p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,p)
    root=ET.parse(source).getroot();tests=list(root.iter('testcase'))
    rows.append(dict(file=str(p.relative_to(out)),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        testcases=len(tests),failures=sum(e.tag=='failure' for t in tests for e in t),
        errors=sum(e.tag=='error' for t in tests for e in t),skipped=sum(e.tag=='skipped' for t in tests for e in t)))
for name in ['components05.json','components05_package_tests.log','build04.json']:
 p=R/'evidence'/name
 if p.exists():shutil.copy2(p,out/name)
(out/'summary.json').write_text(json.dumps(dict(physics_steps=0,tests_rerun=False,files=rows,
 testcases=sum(r['testcases'] for r in rows),failures=sum(r['failures'] for r in rows),
 errors=sum(r['errors'] for r in rows),skipped=sum(r['skipped'] for r in rows)),indent=2)+'\n')
print('Returned existing XML cases',sum(r['testcases'] for r in rows))
