"""Replace only the task's symlink with byte-identical private fixture files."""
from pathlib import Path
import hashlib
import json
import shutil

R=Path('/home/ubuntu/sun/vla_v290_20261021')
P=Path('/home/ubuntu/sun/vla_v289_20261020')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (R/'migration/physical_manifest01.json').exists()
assert not (R/'evidence/physical_batch_status.json').exists()
source=P/'native/fixtures';target=R/'native/fixtures'
assert target.is_symlink() and target.resolve()==source.resolve()
expected={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()}
target.unlink()  # Remove our alias only; the frozen parent directory is untouched.
shutil.copytree(source,target)
actual={str(p.relative_to(target)):sha(p) for p in target.rglob('*') if p.is_file()}
assert actual==expected
(R/'evidence/fixture_paths01.json').write_text(json.dumps(dict(passed=True,physics_steps=0,
    files=actual,parent_unchanged=True,why='Docker target symlink resolved generated profile paths into the parent prefix; ordinary files retain canonical /work/fixtures paths.'),indent=2)+'\n')
