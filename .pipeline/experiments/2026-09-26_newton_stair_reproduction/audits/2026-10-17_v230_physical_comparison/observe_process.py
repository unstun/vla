"""Read-only process/thread snapshot; never attach, signal or pause a process."""
from pathlib import Path
import json,subprocess,time
HERE=Path(__file__).resolve().parent;out=HERE/'results';out.mkdir(exist_ok=True)
root=Path('/data/sun/vla_mppi_20261009/trials/v231_linux_full_attempt01/runs/v231_linux_full_attempt01')
listing=subprocess.check_output(['docker','top','v231-linux-full-attempt01','-eo','pid,args'],text=True)
record={'wall_ns':time.time_ns(),'processes':[]}
for line in listing.splitlines()[1:]:
 if not any(s in line for s in ('controller_server','planner_server','bt_navigator')):continue
 pid=int(line.split()[0]);entry={'pid':pid,'command':line.strip(),'threads':[]}
 for folder in sorted((Path('/proc')/str(pid)/'task').iterdir()):
  try:
   fields=(folder/'stat').read_text().split(') ',1)[1].split()
   entry['threads'].append({'tid':int(folder.name),'state':fields[0],'utime_ticks':int(fields[11]),'stime_ticks':int(fields[12]),'wchan':(folder/'wchan').read_text().strip()})
  except (OSError,ValueError):pass
 record['processes'].append(entry)
state=json.loads((root/'backend_latest.json').read_text())
record['body_stamp_ns']=state['measurement_body_pose']['stamp_ns'];record['jobs']={k:v['status'] for k,v in state.get('jobs',{}).items()}
with (out/'readonly_process_snapshots.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
print(json.dumps(record,indent=2))
