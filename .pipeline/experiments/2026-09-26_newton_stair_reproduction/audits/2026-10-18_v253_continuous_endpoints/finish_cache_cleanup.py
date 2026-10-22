from pathlib import Path
import hashlib,json
BASE=Path('/task');AUDIT=BASE/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-18_v253_continuous_endpoints'
p=AUDIT/'results/intermediate_cleanup.json';r=json.loads(p.read_text());deleted=0
for row in r['files']:
 q=BASE/Path(row['path']).relative_to('/data/sun/vla_mppi_20261009')
 assert 'CMakeFiles' in q.parts and q.name.endswith(('.o','.o.d')) and not q.is_symlink()
 assert q.parts[2].startswith(('recovery_v','environment_score_v','pct_scan_traversability_v','floor_reason_v','support_height_v','blocked_feedback_v','command_continuity_v','callback_failure_v'))
 if q.exists():
  assert hashlib.sha256(q.read_bytes()).hexdigest()==row['sha256'];q.unlink()
 deleted+=row['bytes']
r.update(completed=True,reclaimed_bytes=deleted);p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(completed=True,reclaimed_bytes=deleted)))
