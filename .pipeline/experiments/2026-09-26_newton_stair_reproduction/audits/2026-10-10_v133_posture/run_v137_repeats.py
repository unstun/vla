"""Execute six fixed fresh trials per arm after v137 pilots pass; preserve every outcome."""
from pathlib import Path
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
VERSION=BASE/'versions/v137'
TASK=Path('/data/sun/vla_mppi_20261009')
OUTPUT=TASK/'results/recovery_v137_repeats'
ORDER=[('baseline',1),('candidate',4),('candidate',5),('baseline',2),('candidate',6),('baseline',3),('baseline',4),('candidate',7),('baseline',5),('candidate',8),('candidate',9),('baseline',6)]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def save(path,value):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)

def main():
    assert platform.system()=='Linux' and HERE.is_relative_to(TASK/'repo')
    pilots=json.loads((TASK/'results/recovery_v137_pilots/progress.json').read_text())
    assert pilots['state']=='completed' and len(pilots['completed'])==3
    assert all(r['terminal']=='FINISHED' and not r['fallen'] and r['copyback'] and r['retention']=='completed' for r in pilots['completed'])
    OUTPUT.mkdir(exist_ok=False)
    request={'host':'gpu5070ti','pid':os.getpid(),'order':[{'variant':v,'attempt':a} for v,a in ORDER],
             'protocol_sha256':sha(VERSION/'PLAN.md'),'script_sha256':sha(Path(__file__)),
             'repeat_protocol_sha256':sha(HERE/'REPEAT_PROTOCOL_V136.md'),
             'version_manifest_sha256':sha(VERSION/'manifest.json'),
             'receipts':{v:sha(TASK/'results/recovery_v137'/f'{v}_receipt.json') for v in ('baseline','candidate')},
             'started_unix_s':time.time(),'primary_comparison':True,'scope':'Six fresh trials per arm, ABBA blocks; parent native v136 versus native v137, both with the v135 global map; all failures retained. Candidate acceptance requires six arrivals, no falls, all ownership/copyback/retention gates.'}
    save(OUTPUT/'request.json',request)
    progress={'state':'running','completed':[],'active':None}
    try:
        for index,(variant,attempt) in enumerate(ORDER,1):
            tag=f'v137_{variant}_attempt{attempt:02d}'
            if (TASK/'trials'/tag).exists():raise RuntimeError('Existing trial: '+tag)
            free=shutil.disk_usage(TASK).free
            if free<15*1024**3:raise RuntimeError('Insufficient data disk margin')
            containers=subprocess.check_output(['docker','ps','--format','{{.Names}}'],text=True).strip()
            if containers:raise RuntimeError('Host container already active: '+containers)
            preflight={'index':index,'tag':tag,'unix_s':time.time(),'load':os.getloadavg(),'free_bytes':free,'containers':containers}
            save(OUTPUT/f'{tag}_preflight.json',preflight)
            progress['active']=tag;save(OUTPUT/'progress.json',progress)
            print(json.dumps({'event':'start',**preflight}),flush=True)
            cmd=[sys.executable,str(VERSION/'run_comparison.py'),'--variant',variant,'--attempt',str(attempt)]
            with (OUTPUT/f'{tag}_driver.log').open('w') as stream:
                result=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT,timeout=1000)
            path=TASK/'results/recovery_v137/comparison'/tag/'outcome.json'
            if not path.exists():raise RuntimeError(f'{tag}: missing outcome; exit {result.returncode}')
            outcome=json.loads(path.read_text());m=outcome.get('metrics',{});terminal=m.get('terminal') or {}
            row={'index':index,'tag':tag,'variant':variant,'process_exit':result.returncode,
                 'terminal':terminal.get('backend_terminal_status'),'terminal_note':terminal.get('note'),
                 'fallen':m.get('fallen'),'copyback':m.get('state_copyback_verified'),
                 'retention':outcome.get('retention'),'path_m':m.get('measured_path_m'),
                 'end_sim_s':m.get('actual_physics_end_s'),'outcome_sha256':sha(path)}
            progress['completed'].append(row);progress['active']=None;save(OUTPUT/'progress.json',progress)
            print(json.dumps({'event':'end',**row}),flush=True)
            if result.returncode or outcome.get('retention')!='completed' or not m.get('state_copyback_verified'):
                raise RuntimeError(f'{tag}: execution/retention gate failed; preserve and inspect')
        progress['state']='completed'
    except BaseException as error:
        progress['state']='interrupted';progress['error']=repr(error);raise
    finally:
        progress['updated_unix_s']=time.time();save(OUTPUT/'progress.json',progress)
        print(json.dumps(progress),flush=True)
if __name__=='__main__':main()
