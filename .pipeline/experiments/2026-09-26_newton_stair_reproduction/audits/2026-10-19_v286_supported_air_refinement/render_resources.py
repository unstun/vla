"""Admission for closed-recording postprocessing only, never physical runs."""
from pathlib import Path
import json
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent


def sample():
    closed = json.loads((HERE / 'results/physical_batch_status.json').read_text())
    assert len(closed) == 10 and all(r['stage'] == 'execution_closed_pending_analysis' for r in closed)
    memory = {r.split(':')[0]: int(r.split()[1])*1024
        for r in Path('/proc/meminfo').read_text().splitlines() if r.startswith('MemAvailable:')}
    free_gpu = [int(x.strip()) for x in subprocess.check_output([
        'nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()]
    disk = shutil.disk_usage('/home/sun/vla_exec/physical_runs_v286').free
    row = dict(utc_s=time.time(), physics_steps=0, all_ten_physical_attempts_closed=True,
        available_RAM_bytes=memory['MemAvailable'], free_GPU_MiB=free_gpu,
        output_free_bytes=disk, minimum_RAM_bytes=8*1024**3, minimum_GPU_MiB=2048,
        minimum_disk_bytes=10*1024**3, physical_gate_changed=False,
        GPU_compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory',
            '--format=csv,noheader'],text=True).strip())
    row['passed'] = memory['MemAvailable'] >= row['minimum_RAM_bytes'] and \
        min(free_gpu) >= row['minimum_GPU_MiB'] and disk >= row['minimum_disk_bytes']
    with (HERE / 'results/render_resource_observations.jsonl').open('a') as stream:
        stream.write(json.dumps(row)+'\n')
    return row
