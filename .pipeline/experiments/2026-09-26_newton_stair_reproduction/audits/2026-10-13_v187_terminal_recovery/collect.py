"""Run after the cohort closes; compact five immutable, hash-verified captures."""
import argparse,json
from pathlib import Path
from extract import extract
p=argparse.ArgumentParser();p.add_argument('--task',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
for n in range(1,6):
 tag=f'v187_full_candidate_attempt{n:02d}';trial=a.task/'trials'/tag
 assert (trial/'evidence/execution.json').is_file(),'Do not analyze an active physical run'
 assert (a.task/'results/v187_full_repeats'/tag/'outcome.json').is_file(),'Closeout missing'
 extract(trial/'runs'/tag,a.output/f'attempt{n:02d}')
# Preserve actual capture-state diagnostics with the raw log's member identity.
import hashlib,re,zipfile
for n in range(1,6):
 tag=f'v187_full_candidate_attempt{n:02d}';root=a.task/'trials'/tag/'runs'/tag
 manifest=json.loads((root/'raw_capture_manifest.json').read_text())
 name='nav2.log'
 if (root/name).is_file():data=(root/name).read_bytes()
 else:
  with zipfile.ZipFile(root/'raw_capture.zip') as archive:data=archive.read(name)
 expected=manifest['members'][name]
 assert len(data)==expected['bytes'] and hashlib.sha256(data).hexdigest()==expected['sha256']
 captures=[]
 for line in data.decode().splitlines():
  m=re.search(r'V187_TERMINAL_TIMEOUT generation=(\d+) traj=(\d+) error_m=([0-9.]+) elapsed_s=([0-9.]+)',line)
  if m:captures.append(dict(generation=int(m[1]),trajectory=int(m[2]),error_m=float(m[3]),elapsed_s=float(m[4]),source_line=line))
 (a.output/f'attempt{n:02d}'/'timeout_events.json').write_text(json.dumps({'source':expected,'timeouts':captures},indent=2)+'\n')
