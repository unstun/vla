from pathlib import Path
import hashlib,json,subprocess
R=Path('/home/ubuntu/sun/vla_v287_20261020');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
S=R/'migration/runtime_binding02.json';assert not S.exists()
paths=[R/'environment_score_v224/fixtures/building/environment03.env',R/'migration/offline02.py']
S.write_text(json.dumps(dict(original_migration_manifest_sha256=sha(R/'migration/native_manifest01.json'),files={str(p.relative_to(R)):sha(p) for p in paths},scope='Existing canonical legacy-control field and verifier; no missing mount in this batch'),indent=2)+'\n')
subprocess.run(['python3',str(R/'migration/offline02.py'),'verify'],check=True)
subprocess.run(['python3',str(R/'migration/offline02.py'),'matrix'],check=True)
