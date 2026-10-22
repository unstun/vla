"""Read-only inherited resource gate; does not reserve, stop or launch anything."""
from pathlib import Path
import hashlib,importlib.util,json,time,sys
HERE=Path(__file__).resolve().parent;p=HERE/'resource_admission.py'
spec=importlib.util.spec_from_file_location('inherited_resource_gate196',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
r=dict(utc_epoch_s=time.time(),gate_source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),physics_steps=0,processes_changed=0)
try:r.update(passed=True,resource_admission=module.admit())
except RuntimeError as error:r.update(passed=False,reason=str(error))
q=HERE/'results';q.mkdir(exist_ok=True);tag=sys.argv[1];assert tag.isdigit()
with (q/('resource_check'+tag+'.json')).open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r))
