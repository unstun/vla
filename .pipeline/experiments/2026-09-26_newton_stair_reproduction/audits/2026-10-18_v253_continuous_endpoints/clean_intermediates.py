"""Reclaim old CMake object caches only; preserve all evidence and binaries."""
from pathlib import Path
import hashlib,json,time
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
# No raw/archive/checkpoint/video, installed file, library or test executable.
roots=[p for p in BASE.glob('*/build') if p.parent.name.startswith(('recovery_v','environment_score_v','pct_scan_traversability_v','floor_reason_v','support_height_v','blocked_feedback_v','command_continuity_v','callback_failure_v'))]
rows=[]
for root in roots:
 for p in root.rglob('*'):
  if not p.is_file() or 'CMakeFiles' not in p.parts or not (p.name.endswith('.o') or p.name.endswith('.o.d')):continue
  rows.append(dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
receipt=dict(scope='Old CMake object/dependency intermediates only',created_utc_s=time.time(),files=rows,total_bytes=sum(r['bytes'] for r in rows),preserved='Sources, frozen install/evaluator binaries, test executables, all logs/XML, policies, raw captures and videos')
(HERE/'results/intermediate_cleanup.json').write_text(json.dumps(receipt,indent=2)+'\n')
for row in rows:Path(row['path']).unlink()
print(json.dumps(dict(deleted_objects=len(rows),reclaimed_bytes=receipt['total_bytes'])),flush=True)
