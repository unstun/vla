"""Read-only live library provenance for this cohort's owned native processes."""
from pathlib import Path
import hashlib,json,subprocess,time
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
found={};deadline=time.monotonic()+2800
while time.monotonic()<deadline:
 for cid in ('A02',):
  if cid in found:continue
  name=f'v255-{cid.lower()}-attempt01'
  result=subprocess.run(['docker','top',name,'-eo','pid,comm'],text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
  if result.returncode:continue
  processes=[]
  for line in result.stdout.splitlines()[1:]:
   cols=line.split()
   if len(cols)!=2 or not any(v in cols[1] for v in ('planner_server','controller_serv')):continue
   pid=int(cols[0]);maps=Path(f'/proc/{pid}/maps')
   try:lines=maps.read_text().splitlines()
   except (PermissionError,FileNotFoundError):continue
   files={}
   for entry in lines:
    parts=entry.split(maxsplit=5)
    if len(parts)<6:continue
    p=parts[5]
    if not p.startswith('/work/install/') or not any(v in p for v in ('libpct_route_planner','liblite3_nav2_plugins','libscan_native_core','libscan_nav2_controller')):continue
    host=BASE/'generic_mechanisms_v254/native'/p.removeprefix('/work/')
    files[p]=hashlib.sha256(host.read_bytes()).hexdigest()
   if files:processes.append(dict(host_pid=pid,process=cols[1],mapped_native_libraries=files))
  if len(processes)>=2:
   found[cid]=dict(case_id=cid,captured_utc_s=time.time(),container=name,processes=processes,
    claim='Actual loaded library maps; source/install hashes independently frozen')
   (HERE/'results/live_native_linkage.json').write_text(json.dumps(found,indent=2)+'\n')
   print('captured '+cid,flush=True)
 status=HERE/'results/batch_status.json'
 if status.exists():
  rows=json.loads(status.read_text())
  if len(rows)==1 and all(r['stage']!='running' for r in rows):break
 time.sleep(2)
print(json.dumps(dict(captured=list(found))),flush=True)
