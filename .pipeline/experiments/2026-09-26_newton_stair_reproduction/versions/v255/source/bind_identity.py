"""Freeze preparation identity; source changes after qualification require a new binding."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'manifest.json').exists()
selection=json.loads((HERE/'selection.json').read_text())
assert [r['case_id'] for r in selection['selected']]==['A02','G07','R11']
for item in selection['selected']:assert sha(HERE/'scenarios'/(item['case_id']+'.json'))==item['scenario_sha256']
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()
 and p.relative_to(HERE).parts[0] not in ('source','results','__pycache__')
 and p.name not in ('manifest.json','source_identity.json','RESULTS.md')}
(HERE/'source_identity.json').write_text(json.dumps(dict(version='v255',native='v254',bridge='v248',files=files,
 native_manifest_sha256=sha(HERE.parent/'v254/manifest.json'),offline_gate_sha256=sha(HERE/'results/offline_gate.json')),indent=2)+'\n')
