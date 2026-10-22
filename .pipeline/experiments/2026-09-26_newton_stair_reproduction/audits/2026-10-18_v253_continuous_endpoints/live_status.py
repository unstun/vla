"""Read-only compact live state; never operates on simulator controls."""
from pathlib import Path
import json
ROOT=Path('/data/sun/vla_mppi_20261009/trials/v255_A02_attempt01/runs/v255_A02_attempt01')
r=dict(run='v255_A02_attempt01',raw_exists=ROOT.exists())
p=ROOT/'telemetry.jsonl'
if p.exists():
 with p.open('rb') as f:
  f.seek(max(0,p.stat().st_size-100000));lines=f.read().splitlines()
 for line in reversed(lines):
  try:
   row=json.loads(line);r.update(physics_s=row.get('physics_time_s'),stance_mode=row.get('stance_mode'),position=row.get('body_sensor',{}).get('position'));break
  except json.JSONDecodeError:pass
p=ROOT/'run.log'
if p.exists() and 'physics_s' not in r:
 with p.open('rb') as f:
  f.seek(max(0,p.stat().st_size-100000));lines=f.read().splitlines()
 for line in reversed(lines):
  try:
   row=json.loads(line)
   if 'sim' in row:r.update(physics_s=row['sim'],position=row.get('base'),goal_sent=row.get('goal_sent'),command=row.get('command'),backend_error=row.get('backend_error'));break
  except json.JSONDecodeError:pass
p=ROOT/'result.json' 
if p.exists():
 row=json.loads(p.read_text());r.update(recording_closed=True,physics_duration_s=row.get('physics_duration_s'),fallen=row.get('fallen'),finish_request=row.get('finish_request'))
print(json.dumps(r),flush=True)
