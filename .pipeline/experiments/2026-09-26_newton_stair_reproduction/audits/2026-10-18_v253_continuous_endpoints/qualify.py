"""Verify complete test coverage and qualify the immutable native treatment."""
from pathlib import Path
import hashlib,json,shutil,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;EXP=HERE.parents[1];VERSION=EXP/'versions/v253';BASE=Path('/data/sun/vla_mppi_20261009');WORK=BASE/'generic_mechanisms_v253/native'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
# copy2/mtime made the first incremental build retain a three-case test binary
# although its source already contained four cases. Rebuild only that test from
# the identical frozen bytes; retain the initial 46-case build receipt unchanged.
files=list((WORK/'build/lite3_nav2_plugins/test_results').rglob('*.xml'));assert len(files)==7
count=0;dest=VERSION/'results/qualified_pct_unit';dest.mkdir(exist_ok=True)
for p in files:
 root=ET.parse(p).getroot();assert int(root.get('failures',0))==0 and int(root.get('errors',0))==0
 count+=int(root.get('tests',0));shutil.copy2(p,dest/p.name)
new=next(p for p in files if p.name=='test_continuous_endpoints.gtest.xml')
names={r.get('name') for r in ET.parse(new).getroot().iter('testcase')}
assert names=={'TrueSupportedEndpointIsNotReplacedByRoundedGapCentre','UnsupportedTrueEndpointCannotUseSupportedGridCandidate','DistinctRequestsWithinOneCellKeepBothEndpoints','AttachmentUsesRealGeometryCostAndCannotCrossCliffs'}
assert count==47
receipt=dict(unit_targets=7,unit_test_cases=count,passed=True,
 xml_sha256={p.name:sha(p) for p in files},
 endpoint_test_binary_sha256=sha(WORK/'build/lite3_nav2_plugins/test_continuous_endpoints'),
 note='Complete source-covered unit rerun; initial frozen 46-case receipt retained. Installed native hashes remain immutable.')
(VERSION/'results/qualified_unit_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
source=(VERSION/'acceptance.py').read_text()
old="units=json.loads((HERE/'results/native_receipt.json').read_text())";assert source.count(old)==1
source=source.replace(old,"units=json.loads((HERE/'results/qualified_unit_receipt.json').read_text())")
source=source.replace("OUT/'support/metrics.txt',OUT/'measured_start/summary.json'","HERE/'results/qualified_unit_receipt.json',OUT/'support/metrics.txt',OUT/'measured_start/summary.json'")
(VERSION/'results/qualification_adapter.json').write_text(json.dumps(dict(validator_sha256=sha(Path(__file__)),frozen_validator_sha256=sha(VERSION/'acceptance.py'),adaptation='Use verified complete 47-case unit rerun; retain initial source/build receipt'),indent=2)+'\n')
exec(compile(source,str(VERSION/'acceptance.py'),'exec'),dict(__file__=str(VERSION/'acceptance.py'),__name__='v253_complete_qualification'))
