"""Read-only admission for the user-authorized bounded CPU simulation."""
from pathlib import Path
import json,subprocess,time,shutil
def admit():
 m=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
 available=int(m['MemAvailable'].split()[0])*1024
 gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],text=True).strip()
 low,high=map(int,Path('/proc/sys/net/ipv4/ip_local_port_range').read_text().split())
 if any(low<=port<=high for port in (24600,24601,24602,24603,24651)):raise RuntimeError('Service ports overlap ephemeral range')
 free=shutil.disk_usage('/data/sun/vla_mppi_20261009').free
 record={'utc_epoch_s':time.time(),'available_bytes':available,'gpu_compute':gpu,'free_disk_bytes':free,'minimum_available_bytes':20*1024**3}
 if available<20*1024**3 or gpu or free<10*1024**3:raise RuntimeError('Resource admission held: '+json.dumps(record))
 return record


def wait_for_ports():
 import socket
 begin=time.monotonic()
 while True:
  occupied=[]
  for port in (24600,24601,24602,24603,24651,8785):
   try:
    with socket.socket() as probe:probe.bind(('0.0.0.0',port))
   except OSError:occupied.append(port)
  if not occupied:return time.monotonic()-begin
  if time.monotonic()-begin>=120:raise RuntimeError('Ports remain unavailable: '+str(occupied))
  time.sleep(5)
