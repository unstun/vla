"""Exercise the real managed/supervisor/retention path before Newton launch."""
from pathlib import Path
import json,os,subprocess,sys,tempfile

HERE=Path(__file__).resolve().parent
root=Path(tempfile.mkdtemp(prefix='vla_newton_v74_contract_',dir='/private/tmp'))
(root/'scripts').mkdir();(root/'scripts/run_bounded.py').symlink_to(HERE/'mac_supervisor.py')
run='v74_manager_contract';(root/'runs'/run/'artifacts/external_episode').mkdir(parents=True)
env=os.environ.copy();env['V74_TEMP_ROOT']=str(root)
child="from pathlib import Path;import json,os;Path(os.environ['NEWTON_RUN_DIR'],'result.json').write_text(json.dumps({'status':'component_contract','physics_run':False}))"
command=[sys.executable,str(HERE/'mac_managed.py'),'--run-id',run,'--deadline','10',
    '--retention','archive','--',sys.executable,'-c',child]
p=subprocess.run(command,env=env,capture_output=True,text=True,timeout=20)
assert p.returncode==0,(p.stdout,p.stderr)
assert json.loads((root/'runs'/run/'process.json').read_text())['exit_code']==0
assert json.loads((root/'runs'/run/'retention_result.json').read_text())['status']=='completed'
repeated=subprocess.run(command,env=env,capture_output=True,text=True,timeout=20)
assert repeated.returncode!=0 and 'Run already contains data' in repeated.stderr
print('V74_COMPLETE_MANAGER_SUPERVISOR_RETENTION_PASS',root)
