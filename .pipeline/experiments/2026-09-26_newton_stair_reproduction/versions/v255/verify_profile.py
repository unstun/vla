"""Original numerical gates with the explicitly authorized native-map ablation."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'v233/verify_profile.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify(root):
 source=PARENT.read_text()
 before=' for key in old_pct:assert pct[key]==old_pct[key],(key,pct[key],old_pct[key])'
 assert source.count(before)==1
 source=source.replace(before," for key in old_pct:\n  if key!='map_bundle':assert pct[key]==old_pct[key],(key,pct[key],old_pct[key])")
 ns=dict(__file__=str(PARENT),__name__='original_numerical_profile')
 exec(compile(source,str(PARENT),'exec'),ns);report=ns['verify'](root)
 pct=report['pct'];assert pct['map_bundle']=='/work/fixtures/building/native_original.pct'
 assert pct['static_support_path']=='/work/fixtures/building/native.support'
 manifest=json.loads((HERE.parent/'v247/manifest.json').read_text())
 assert pct['static_support_fnv64']==manifest['static_support_fnv64']
 work=Path('/data/sun/vla_mppi_20261009/generic_mechanisms_v254/native/fixtures/building')
 receipt=json.loads((HERE.parent/'v247/results/fixture_receipt.json').read_text())
 assert sha(work/'native_original.pct')==receipt['route_sha256']
 assert sha(work/'native.support')==manifest['static_support_sha256']
 report.update(original_numerical_verifier_sha256=sha(PARENT),authorized_native_map_sha256=receipt['route_sha256'],
  static_support_sha256=manifest['static_support_sha256'],configuration_changes='Restore native cost map; shared physical support; all original numerical gates retained')
 (root/'configuration_gate.json').write_text(json.dumps(report,indent=2)+'\n');return report
