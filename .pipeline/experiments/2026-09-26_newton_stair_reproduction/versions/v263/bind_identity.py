"""Bind the qualified matrix selection before zero-step process preflights."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'manifest.json').exists()
selection=json.loads((HERE/'selection.json').read_text());assert selection['physical_admission_passed'] and len(selection['selected'])==10
assert {'A04','G05','CU06'}<={r['case_id'] for r in selection['selected']}
for item in selection['selected']:assert sha(HERE/'scenarios'/(item['case_id']+'.json'))==item['scenario_sha256']
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and p.relative_to(HERE).parts[0] not in ('source','results','__pycache__') and p.name not in ('manifest.json','source_identity.json','RESULTS.md') and '__pycache__' not in p.parts}
(HERE/'source_identity.json').write_text(json.dumps(dict(version='v263',native='v261',benchmark='v262',bridge='v248',files=files,
 native_manifest_sha256=sha(HERE.parent/'v261/manifest.json'),benchmark_manifest_sha256=sha(HERE.parent/'v262/manifest.json'),
 explicit_heading_driver_sha256=sha(HERE.parent/'v257/long_route_driver.py'),offline_gate_sha256=sha(HERE/'results/offline_gate.json')),indent=2)+'\n')
