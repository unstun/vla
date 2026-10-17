"""Apply the v196 acceptance predicates with only the declared version identity rebound."""
from pathlib import Path
import hashlib,importlib.util,json,sys
HERE=Path(__file__).resolve().parent;VERSIONS=HERE.parents[2];V196=VERSIONS/'v196'
sys.path.insert(0,str(V196))
from analyze_remote import analyze,Capture
raw=Path('/private/tmp/vla_v204_physics_20261015/runs/v204_mac_full_attempt01')
source=(V196/'verify_full_route.py').read_text()
before="request['integration_version'] == 'v196'";assert source.count(before)==1
source=source.replace(before,"request['integration_version'] == 'v204'").replace("'v196 native / v196 shared-state Option B direct Nav2 + SCAN candidate on '","'v204 native / inherited shared-state Option B direct Nav2 + SCAN on '")
(HERE/'executed_full_route_verifier.py').write_text(source)
namespace={'__file__':str(V196/'verify_full_route.py'),'__name__':'v204_acceptance'}
exec(compile(source,str(HERE/'executed_full_route_verifier.py'),'exec'),namespace)
try:gate=namespace['verify'](raw)
except Exception as error:gate=dict(passed=False,error=repr(error),run=raw.name)
(HERE/'full_route_verification.json').write_text(json.dumps(gate,indent=2)+'\n')
try:
 analyze(raw,HERE,True)
 p=HERE/'metrics.json'
 if p.exists():
  data=json.loads(p.read_text());data['native_version']='Nav2 Foxy linux/arm64 native v204 SCAN'
  p.write_text(json.dumps(data,indent=2)+'\n')
except Exception as error:
 (HERE/'analysis_error.json').write_text(json.dumps(dict(error=repr(error)),indent=2)+'\n')
capture=Capture(raw);result=capture.json('result.json')
summary=dict(run=raw.name,full_route_gate_passed=gate['passed'],terminal_status=result.get('finish_request',{}).get('backend_terminal_status'),fallen=gate.get('fallen',result.get('fallen')),physics_duration_s=result.get('physics_duration_s'),raw_root=str(raw),verifier_source_sha256=hashlib.sha256((V196/'verify_full_route.py').read_bytes()).hexdigest(),verifier_version_assertion_only_rebound=True)
(HERE/'outcome.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
