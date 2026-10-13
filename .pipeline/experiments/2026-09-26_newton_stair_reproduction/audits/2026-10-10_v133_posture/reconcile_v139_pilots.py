"""Preserve the disconnected runner record; verify all already-closed pilots."""
from pathlib import Path
import hashlib,json,subprocess,sys
T=Path('/data/sun/vla_mppi_20261009');B=Path(__file__).resolve().parents[2];O=T/'results/recovery_v139_02_pilots'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 original=O/'progress.json';p=json.loads(original.read_text())
 assert p['state'] in ('completed','interrupted') and p['active'] is None
 if p['state']=='interrupted':assert p['error']=="BrokenPipeError(32, 'Broken pipe')"
 assert [r['tag'] for r in p['completed']]==[f'v139_candidate_attempt{i:02d}' for i in range(1,4)]
 subprocess.run([sys.executable,str(B/'versions/v139/freeze_host.py'),'verify'],check=True)
 for r in p['completed']:
  f=T/'results/recovery_v139_02/comparison'/r['tag']/'outcome.json';assert sha(f)==r['outcome_sha256']
  o=json.loads(f.read_text());m=o['metrics'];assert m['terminal']['backend_terminal_status']=='FINISHED' and not m['fallen'] and m['state_copyback_verified'] and o['retention']=='completed' and r['process_exit']==0
 out=O/'reconciled_gate.json';assert not out.exists()
 out.write_text(json.dumps({'state':'completed','completed':p['completed'],'original_progress_sha256':sha(original),'reason':'All three closed outcomes verified. Original interrupted progress preserved: final runner output hit a disconnected SSH pipe. No trial rerun or replacement.','script_sha256':sha(Path(__file__))},indent=2)+'\n')
 print(json.dumps({'passed':True,'arrivals':3,'runs':3,'falls':0,'gate_sha256':sha(out)}))
if __name__=='__main__':main()
