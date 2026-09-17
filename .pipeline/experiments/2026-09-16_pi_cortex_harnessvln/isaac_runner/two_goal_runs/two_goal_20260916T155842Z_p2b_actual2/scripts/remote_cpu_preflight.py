#!/usr/bin/env python3
import argparse, hashlib, json, subprocess
from pathlib import Path

def sha256(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write_json(path, payload):
    path=Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True)+'\n', encoding='utf-8')
def run(cmd, log, timeout=180, check=True):
    p=subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
    Path(log).write_text(p.stdout, encoding='utf-8')
    if check and p.returncode: raise RuntimeError('command failed exit=%s tail=%s'%(p.returncode,p.stdout[-2000:]))
    return p

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--run-root', required=True); ap.add_argument('--foxy-image-id', required=True); ap.add_argument('--remote-scan-workspace', required=True); ns=ap.parse_args()
    root=Path(ns.run_root); artifacts=root/'artifacts'; logs=artifacts/'cpu_preflight_logs'; logs.mkdir(parents=True, exist_ok=True)
    result={'passed':False,'cpu_only':True,'isaac_started':False,'gpu_required':False}
    try:
        scan=Path(ns.remote_scan_workspace)
        if not (scan/'install/setup.bash').is_file(): raise RuntimeError('missing scan install/setup.bash')
        image=subprocess.check_output(['podman','image','inspect','--format','{{.Id}}',ns.foxy_image_id], text=True).strip().removeprefix('sha256:')
        if image != ns.foxy_image_id: raise RuntimeError('foxy image mismatch '+image)
        script=(root/'scripts/backend_start_cpu_preflight.sh').read_text(encoding='utf-8')
        if 'set -u' in script or '& &&' in script: raise RuntimeError('unsafe backend shell')
        run(['bash','-n',str(root/'scripts/backend_start_cpu_preflight.sh')], logs/'bash_n.log')
        name='vla-p2b-cpu-preflight-'+root.name.lower().replace('_','-')
        subprocess.run(['podman','rm','-f',name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        base=['podman','run','--rm','--pull=never','--network=host','--name',name,'-e','ROS_DOMAIN_ID=94','-e','ROS_LOCALHOST_ONLY=1','-v',str(root/'backend_ros')+':/backend_ros:ro','-v',str(root/'backend_adapter')+':/backend_adapter:ro','-v',str(root/'navigation_service')+':/navigation_service:ro','-v',str(root/'bridge')+':/bridge:ro','-v',str(root/'config')+':/config:rw','-v',str(logs)+':/logs:rw','-v',str(root/'scripts')+':/scripts:ro','-v',str(scan)+':/workspace:ro',ns.foxy_image_id]
        import_script="""set -eo pipefail
source /opt/ros/foxy/setup.bash
source /workspace/install/setup.bash
export ROS_DOMAIN_ID=94
export ROS_LOCALHOST_ONLY=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/backend_ros:/backend_adapter:/bridge:${PYTHONPATH:-}
python3 - <<'PY_INNER'
import json
from pathlib import Path
from backend_adapter.p2a_bridge import load_p2a_core
core=load_p2a_core()
import scan_planner_msgs.msg as msg
import p2b_backend_ros.node as node
from p2b_backend_ros.config import load_runtime_config, render_wire_contract
cfg=load_runtime_config(Path('/config/p2b_backend_ros.two_goal.resolved.json'), {})
print(json.dumps({'p2a_core':str(Path(core.__file__).resolve()),'node':str(Path(node.__file__).resolve()),'has_P2BRoute':hasattr(msg,'P2BRoute'),'schema':render_wire_contract(cfg)['schema'],'run_epoch_ns':cfg['run_epoch_ns']}, sort_keys=True))
PY_INNER
python3 -m p2b_backend_ros.node --config /config/p2b_backend_ros.two_goal.resolved.json --print-contract >/logs/print_contract.json
"""
        import_cmd=base+['bash','-lc',import_script]
        write_json(artifacts/'cpu_preflight_import_command.json', import_cmd)
        imp=run(import_cmd, logs/'import.log')
        result['import_tail']=imp.stdout.strip().splitlines()[-5:]
        startup_cmd=base+['bash','-lc','timeout 8s bash /scripts/backend_start_cpu_preflight.sh']
        write_json(artifacts/'cpu_preflight_startup_command.json', startup_cmd)
        st=run(startup_cmd, logs/'startup.log', timeout=60, check=False)
        result['startup_exit_code']=st.returncode; result['startup_expected_timeout']=st.returncode==124
        if st.returncode not in (0,124): raise RuntimeError('startup failed before timeout exit=%s'%st.returncode)
        result['passed']=True
    except Exception as e:
        result['error']=str(e); raise
    finally:
        write_json(artifacts/'cpu_preflight_result.json', result)
        hashes={p.relative_to(artifacts).as_posix():sha256(p) for p in artifacts.rglob('*') if p.is_file()}
        write_json(artifacts/'cpu_preflight_artifact_hashes.json', hashes)
if __name__=='__main__': main()
