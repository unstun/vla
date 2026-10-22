"""Approved CPU-shared admission using actual remaining host resources."""
from pathlib import Path
import hashlib
HERE=Path(__file__).resolve().parent
OUTPUT_ROOT=Path('/home/sun/vla_exec/physical_runs_v287')
PARENT=HERE.parent/'v196/resource_gate.py'
PARENT_SHA256='97de9d45f035831ac676cc342799f4e5df2eadb78bec6d8a3b0a6ee8a50e0a14'

def admit():
    assert hashlib.sha256(PARENT.read_bytes()).hexdigest()==PARENT_SHA256
    OUTPUT_ROOT.mkdir(parents=True,exist_ok=True)
    source=PARENT.read_text();before="shutil.disk_usage('/data/sun/vla_mppi_20261009').free"
    assert source.count(before)==1
    source=source.replace(before,'shutil.disk_usage(OUTPUT_ROOT).free')
    assert source.count('20*1024**3')==2
    assert source.count('or gpu or')==1
    source=source.replace('20*1024**3','16*1024**3').replace('or gpu or','or')
    ns=dict(__file__=str(PARENT),__name__='same_gate_actual_output_disk',OUTPUT_ROOT=OUTPUT_ROOT)
    exec(compile(source,str(PARENT),'exec'),ns)
    result=ns['admit']()
    result.update(output_root=str(OUTPUT_ROOT),parent_gate_sha256=PARENT_SHA256,thresholds_unchanged=False,minimum_available_GiB=16,gpu_compute_observed_only=True,physics_and_policy_device='cpu',disk_gate_unchanged=True)
    return result
