"""Same inherited thresholds, evaluated on the actual physical output filesystem."""
from pathlib import Path
import hashlib
HERE=Path(__file__).resolve().parent
OUTPUT_ROOT=Path('/home/sun/vla_exec/physical_runs_v283')
PARENT=HERE.parent/'v196/resource_gate.py'
PARENT_SHA256='97de9d45f035831ac676cc342799f4e5df2eadb78bec6d8a3b0a6ee8a50e0a14'

def admit():
    assert hashlib.sha256(PARENT.read_bytes()).hexdigest()==PARENT_SHA256
    OUTPUT_ROOT.mkdir(parents=True,exist_ok=True)
    source=PARENT.read_text();before="shutil.disk_usage('/data/sun/vla_mppi_20261009').free"
    assert source.count(before)==1
    source=source.replace(before,'shutil.disk_usage(OUTPUT_ROOT).free')
    ns=dict(__file__=str(PARENT),__name__='same_gate_actual_output_disk',OUTPUT_ROOT=OUTPUT_ROOT)
    exec(compile(source,str(PARENT),'exec'),ns)
    result=ns['admit']()
    result.update(output_root=str(OUTPUT_ROOT),parent_gate_sha256=PARENT_SHA256,thresholds_unchanged=True)
    return result
