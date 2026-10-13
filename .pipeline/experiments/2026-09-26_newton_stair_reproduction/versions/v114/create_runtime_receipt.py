"""Verify the exact native overlay and unchanged v102 runtime inside Foxy."""
from pathlib import Path
import hashlib
import json
import platform

here=Path(__file__).resolve().parent
workspace=Path('/task/v114_workspace')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert platform.machine()=='aarch64'
receipt=json.loads((here.parent/'v102/runtime_receipt.json').read_text())
for name,expected in receipt['runtime_file_sha256'].items():
    assert sha(Path(name))==expected,name
candidate=json.loads((workspace/'candidate_source_identity.json').read_text())
for name,expected in candidate.items():
    assert sha(workspace/name)==expected,name
for source in (here/'src').rglob('*'):
    if source.is_file() and '__pycache__' not in source.parts:
        assert sha(source)==sha(workspace/'src'/source.relative_to(here/'src')),str(source)
for directory in ('src','install'):
    for file in (workspace/directory).rglob('*'):
        if file.is_file() and '__pycache__' not in file.parts:
            receipt['runtime_file_sha256'][str(file)]=sha(file)
assert sha(Path('/task/packages.tsv'))==receipt['package_receipt_sha256']
receipt.update(underlay_version='v102',overlay_version='v114',overlay_packages=[
    'plan_env','path_searching','bspline_opt','scan_planner','scan_nav2_controller','geometry_probe'])
Path('/task/v114-runtime_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'passed':True,'runtime_files':len(receipt['runtime_file_sha256'])}))
