"""Snapshot compact preflight/resource evidence; exclude builds and raw episodes."""
from pathlib import Path
import hashlib
import json
import time

HERE = Path(__file__).resolve().parent
BASE = Path('/data/sun/vla_mppi_20261009')
DEST = HERE / 'auxiliary'
roots = dict(analysis_preflight=BASE / 'v282_analysis_preflight',
             case_preflights=BASE / 'generalization_v282')
files = {}
for prefix, root in roots.items():
    for source in root.rglob('*'):
        relative = source.relative_to(root)
        if not source.is_file() or any(x in relative.parts for x in ('build', 'ros_home', 'ros_logs', '__pycache__')):
            continue
        if source.suffix not in ('.json', '.jsonl', '.log', '.txt') or source.stat().st_size > 4 * 1024**2:
            continue
        files[f'{prefix}/{relative}'] = source
for name in ('resource_watch/latest.json', 'resource_watch/samples.jsonl',
             'preflight_batch_status.json', 'physical_batch_status.json',
             'watch_resources_01.log', 'run_preflights_01.log', 'physical_batch01.log'):
    source = HERE / 'results' / name
    if source.is_file():
        files['monitor/' + name] = source
inventory = {}
for rel, source in files.items():
    data = source.read_bytes()
    target = DEST / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    inventory[rel] = dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), remote_path=str(source))
(DEST / 'return_inventory.json').write_text(json.dumps(dict(snapshot_utc_s=time.time(), files=inventory), indent=2) + '\n')
print(json.dumps(dict(files=len(inventory), bytes=sum(x['bytes'] for x in inventory.values()))))
