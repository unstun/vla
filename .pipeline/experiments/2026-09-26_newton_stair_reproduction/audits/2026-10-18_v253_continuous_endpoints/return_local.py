"""Explicit manifest-bound sync back; never fetch raw arrays or build directories."""
from pathlib import Path
import json,subprocess
HERE=Path(__file__).resolve().parent
REMOTE='gpu5070ti:/data/sun/vla_mppi_20261009/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-18_v253_continuous_endpoints/'
subprocess.run(['rsync','-az',REMOTE+'return_manifest.json',str(HERE/'return_manifest.json')],check=True)
r=json.loads((HERE/'return_manifest.json').read_text());rows=list(r['entries'])
for rel in rows:
 p=Path(rel);assert not p.is_absolute() and '..' not in p.parts and 'CMakeFiles' not in p.parts and 'build' not in p.parts
 assert p.suffix not in ('.zip','.npy','.npz','.f32','.o','.pyc')
listing=HERE/'results/return_files.txt';listing.write_text('\n'.join(rows)+'\n')
subprocess.run(['rsync','-az','--files-from='+str(listing),REMOTE,str(HERE)+'/'],check=True)
print(json.dumps(dict(returned_files=len(rows),returned_bytes=r['return_bytes'])),flush=True)
