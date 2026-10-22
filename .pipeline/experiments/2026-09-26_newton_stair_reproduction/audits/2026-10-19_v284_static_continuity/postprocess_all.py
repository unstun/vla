"""Analyze two independent closed recordings at a time; never replay actuation."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib,json,os,subprocess,sys,time,threading
from render_resources import sample
from physical_support_margins import audit as audit_support
from command_audit import audit as audit_commands
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
STOP=threading.Event()


def process(row):
    cid=row['case_id'];began=time.monotonic()
    if STOP.is_set():return dict(case_id=cid,skipped_after_peer_failure=True,physics_steps=0)
    receipt=HERE/'physical'/cid/'results/local_video_delivery.json'
    if receipt.exists():
        video=json.loads(receipt.read_text());path=Path(video['video'])
        assert path.is_file() and not path.is_symlink()
        assert hashlib.sha256(path.read_bytes()).hexdigest()==video['sha256']
        audit_support(cid);audit_commands(cid)
        return dict(case_id=cid,exit_code=0,already_delivered=True,physics_steps=0)
    while not sample()['passed']:
        if STOP.is_set():return dict(case_id=cid,skipped_after_peer_failure=True,physics_steps=0)
        time.sleep(30)
    number=next(n for n in range(1,1000) if not (BASE/f'v284_{cid}_analysis{n:02d}.log').exists())
    with (BASE/f'v284_{cid}_analysis{number:02d}.log').open('x') as log:
        code=subprocess.run(['nice','-n','10',sys.executable,str(HERE/'postprocess_case.py')],
            env=dict(os.environ,V284_CASE_ID=cid,V284_RENDER_ID=f'{number:02d}'),stdout=log,stderr=subprocess.STDOUT).returncode
    if code==0:
        audit_support(cid);audit_commands(cid)
    else:STOP.set()
    return dict(case_id=cid,exit_code=code,wall_s=time.monotonic()-began,physics_steps=0)


def main():
    rows=json.loads((HERE/'results/physical_batch_status.json').read_text())
    assert len(rows)==10 and all(r['formal_attempt_started'] and r['stage']=='execution_closed_pending_analysis' for r in rows)
    (HERE/'results/analysis_execution_policy.json').write_text(json.dumps(dict(
        physics_steps=0,parallel_workers=2,all_ten_physical_attempts_closed=True,
        distinct_case_outputs=True,resource_gate='>=8 GiB available RAM, >=2 GiB free GPU, >=10 GiB output; shared host allowed'),indent=2)+'\n')
    results=[];errors=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending={pool.submit(process,row):row['case_id'] for row in rows}
        for future in as_completed(pending):
            try:result=future.result()
            except Exception as error:
                STOP.set();result=dict(case_id=pending[future],exit_code=1,error=repr(error),physics_steps=0)
            results.append(result)
            temporary=HERE/'results/analysis_batch_status.tmp'
            temporary.write_text(json.dumps(results,indent=2)+'\n');temporary.replace(HERE/'results/analysis_batch_status.json')
            print(json.dumps(result),flush=True)
            if result.get('exit_code',0):errors.append(result)
    if errors:raise SystemExit('Recorded-state analysis failed; inspect preserved logs, no physical retry')


if __name__=='__main__':main()
