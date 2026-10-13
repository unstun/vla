"""Sequential bounded trials; analyze each closed run before starting the next."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import socket
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
TASK=Path('/data/sun/vla_mppi_20261009')
OUTPUT=TASK/'results/recovery_v134/comparison'

def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024**2),b''):digest.update(chunk)
    return digest.hexdigest()

def wait_ports():
    deadline=time.monotonic()+180
    while True:
        try:
            for port in (46200,46201,46202,46203,8785):
                with socket.socket() as sock:sock.bind(('127.0.0.1',port))
            return
        except OSError:
            if time.monotonic()>deadline:raise
            time.sleep(1)

def main():
    p=argparse.ArgumentParser();p.add_argument('--variant',choices=('baseline','candidate'),required=True)
    p.add_argument('--attempt',type=int,required=True);args=p.parse_args()
    tag=f'v134_{args.variant}_attempt{args.attempt:02d}'
    out=OUTPUT/tag;out.mkdir(parents=True,exist_ok=False)
    subprocess.run([sys.executable,str(HERE/'freeze_host.py'),'verify'],check=True)
    wait_ports()
    process=subprocess.run([sys.executable,str(HERE/'run_remote_corner.py'),'--variant',args.variant,'--attempt',str(args.attempt)],timeout=650)
    trial=TASK/'trials'/tag;root=trial/'runs'/tag
    outcome={'tag':tag,'variant':args.variant,'execution_exit':process.returncode}
    # Record failures as failures; no missing result is inferred to be a success.
    try:
        with (out/'analysis.log').open('w') as stream:
            subprocess.run([sys.executable,str(HERE/'analyze_remote.py'),'--run-root',str(root),
                '--output',str(out),'--metrics-only'],stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=180)
        metrics=json.loads((out/'metrics.json').read_text())
        with (out/'latency.csv').open() as stream:
            slow=[row for row in csv.DictReader(stream) if float(row['solve_ms'])>60]
        metrics['planning']['over_60ms']={'rounds':len(slow),'successful':sum(int(r['success']) for r in slow),
                                         'failed':sum(not int(r['success']) for r in slow)}
        (out/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
        outcome.update(metrics=metrics)
        outcome['retention']=json.loads((root/'retention_result.json').read_text())['status']
    except Exception as error:
        outcome['analysis_error']=repr(error)
    artifacts={'root':str(trial),'files':{str(p.relative_to(trial)):{'bytes':p.stat().st_size,'sha256':sha(p)}
        for p in sorted(trial.rglob('*')) if p.is_file() and not p.is_symlink()}}
    (out/'remote_artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n')
    (out/'outcome.json').write_text(json.dumps(outcome,indent=2)+'\n')
    print(json.dumps(outcome),flush=True)
    if 'analysis_error' in outcome or process.returncode:raise SystemExit(1)

if __name__=='__main__':main()
