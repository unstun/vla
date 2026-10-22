"""Execute one frozen53 batch under the user's acknowledged shared host load."""
from pathlib import Path
import subprocess,time,json,hashlib,datetime
R=Path('/home/ubuntu/sun/vla_v289_20261020')
assert not (R/'benchmark/native_ledger.json').exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(R/'evidence/user_load_decision01.json').write_text(json.dumps(dict(
    user_message='没有空档，就有负载干扰你不能做吗',
    interpretation='Proceed under existing background load, do not stop other jobs. Record interference; strict 1.5s gate remains.',
    timing_exception=False,hard_radius_m=.35,sensor_period_s=.1),ensure_ascii=False,indent=2)+'\n')
start=time.monotonic()
with (R/'evidence/offline_matrix01.log').open('x') as log, (R/'evidence/offline_host_load01.jsonl').open('x') as load:
    child=subprocess.Popen(['python3',str(R/'migration/offline.py'),'matrix'],stdout=log,stderr=subprocess.STDOUT)
    previous=None
    while True:
        counters=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:]))
        busy=None
        if previous:
            d=[b-a for a,b in zip(previous,counters)]
            busy=1-(d[3]+d[4])/sum(d)
        previous=counters
        ledger=R/'benchmark/native_ledger.json'
        try:rows=json.loads(ledger.read_text()) if ledger.exists() else []
        except json.JSONDecodeError:rows=[]
        load.write(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            elapsed_s=time.monotonic()-start,cpu_busy_fraction=busy,
            loadavg=Path('/proc/loadavg').read_text().strip(),
            native_finished=sum(r['state']=='finished' for r in rows),
            current_case=next((r['case_id'] for r in rows if r['state']=='started'),None)))+'\n');load.flush()
        code=child.poll()
        if code is not None:break
        time.sleep(5)
receipt=dict(returncode=code,wall_s=time.monotonic()-start,load_context='Acknowledged concurrent CARLA/ROS workload',
    driver_sha256=sha(R/'migration/offline.py'),native_input_manifest_sha256=sha(R/'migration/native_manifest01.json'),physics_steps=0)
gate=R/'benchmark/offline_gate.json'
if gate.exists():receipt['gate']=json.loads(gate.read_text())
(R/'evidence/offline_matrix01_closed.json').write_text(json.dumps(receipt,indent=2)+'\n')
raise SystemExit(code)
