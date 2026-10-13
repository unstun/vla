"""Bind actual terminal failures to cancellation, policy zero and replacement proof."""
from pathlib import Path
import argparse,gzip,json

def verify(folder,proof_path):
 native=json.loads((folder/'timeout_events.json').read_text())
 rows=[json.loads(x) for x in gzip.open(folder/'telemetry.jsonl.gz','rt')]
 events=[json.loads(x) for x in gzip.open(folder/'events.jsonl.gz','rt')]
 proof=json.loads(proof_path.read_text());results=[]
 for timeout in native['timeouts']:
  gen=timeout['generation']
  cancels=[r for r in events if r['event']=='scan_cancel' and r['data']['generation']==gen and r['data']['reason']=='scan_terminal_correction_timeout']
  first=min(cancels,key=lambda r:r['clock_ns']) if cancels else None
  t=first['clock_ns']/1e9 if first else None
  zero=next((r for r in rows if t is not None and t-.05<=r['physics_time_s']<=t+.3 and max(map(abs,r['effective_command']))<1e-6),None)
  replacement=[r for r in proof['entries'] if r['old_generation']==gen]
  result=dict(timeout,exact_reason_cancel=first['data'] if first else None,
   cancel_sim_s=t,first_policy_zero_sim_s=zero['physics_time_s'] if zero else None,
   policy_zero_delay_s=zero['physics_time_s']-t if zero else None,
   replacement_entries=replacement,replacement_observed=bool(replacement),
   all_observed_replacements_have_measured_proof=all(r['passed'] for r in replacement))
  result['passed']=bool(first and zero and all(r['passed'] for r in replacement))
  results.append(result)
 return {'run':proof['run'],'timeout_events':results,'exercised':bool(results),
  'passed':all(r['passed'] for r in results),
  'claim':'Actual tagged cancel, actual model-input zero within0.3s, and measured proof for any replacement. No-event trials are not timeout-recovery exposure.'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--proof',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(a.input,a.proof);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
