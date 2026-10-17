"""Read immutable v206 inputs used by both diagnostic and physical checks."""
from pathlib import Path
import hashlib
import importlib.util
import json
import zipfile

RAW = Path('/data/sun/vla_mppi_20261009/trials/v206_linux_full_attempt02/runs/v206_linux_full_attempt02')
SEEDS = {'zero_boundary':115.54812622070312, 'quiet_blocked':120.2855224609375}


def load_module(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def telemetry():
    with zipfile.ZipFile(RAW/'raw_capture.zip') as z:
        data=z.read('telemetry.jsonl')
    item=json.loads((RAW/'raw_capture_manifest.json').read_text())['members']['telemetry.jsonl']
    assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
    return [json.loads(line) for line in data.splitlines()], item


def seed_row(name):
    rows,receipt=telemetry()
    row=min(rows,key=lambda r:abs(r['physics_time_s']-SEEDS[name]))
    assert abs(row['physics_time_s']-SEEDS[name])<1e-9
    assert row['policy_owns_joints']
    return row,receipt
