"""Independent recorded-data audits after all physical/video jobs have closed."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,subprocess,sys,time
R=Path('/home/ubuntu/sun/vla_v290_20261021')
def run(name):
    p=R/'migration'/name;log=R/'evidence'/(name[:-3]+'01.log');start=time.monotonic()
    with log.open('x') as stream:
        code=subprocess.run([sys.executable,str(p)],stdout=stream,stderr=subprocess.STDOUT).returncode
    return dict(script=name,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),exit_code=code,
        log=str(log),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),wall_s=time.monotonic()-start)
def main():
    assert (R/'physical_return/return_inventory.json').exists()
    names=['startup_audit.py','input_order_audit.py','boundary_witnesses.py','summarize_mechanisms02.py']
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,names))
    if all(r['exit_code']==0 for r in rows):rows.append(run('final_verify_remote.py'))
    (R/'evidence/post_collect01.json').write_text(json.dumps(dict(physics_steps=0,checks=rows,
        passed=all(r['exit_code']==0 for r in rows)),indent=2)+'\n')
    print(json.dumps(rows),flush=True)
if __name__=='__main__':main()
