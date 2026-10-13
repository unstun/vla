"""Read-only admission for the user-authorized bounded CPU simulation."""
from pathlib import Path
import json,subprocess,time,shutil
def admit():
 m=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
 available=int(m['MemAvailable'].split()[0])*1024
 gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],text=True).strip()
 free=shutil.disk_usage('/data/sun/vla_mppi_20261009').free
 record={'utc_epoch_s':time.time(),'available_bytes':available,'gpu_compute':gpu,'free_disk_bytes':free,'minimum_available_bytes':20*1024**3}
 if available<20*1024**3 or gpu or free<10*1024**3:raise RuntimeError('Resource admission held: '+json.dumps(record))
 return record
