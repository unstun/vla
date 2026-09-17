#!/usr/bin/env python3
"""CPU-only backend preflight for a prepared two-goal pilot package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
from typing import List

FOXY_IMAGE_ID = "e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8"
DEFAULT_REMOTE_ROOT = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/two_goal_cpu_preflight"
DEFAULT_REMOTE_SCAN = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_03"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_backend_script() -> str:
    return """set -eo pipefail
source /opt/ros/foxy/setup.bash
source /workspace/install/setup.bash
export ROS_DOMAIN_ID=94
export ROS_LOCALHOST_ONLY=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/backend_ros:/backend_adapter:/bridge:${PYTHONPATH:-}
ros2 run scan_planner scan_planner_node --ros-args --params-file /config/planner.yaml -r body_pose:=/quad_0/body_pose -r sensor_pose:=/quad_0/lidar_pose -r cloud:=/quad_0/cloud > /logs/scan_planner_node.log 2>&1 &
scan_pid=$!
ros2 run scan_planner closed_loop_controller --ros-args --params-file /config/controller.yaml -r body_pose:=/quad_0/body_pose > /logs/closed_loop_controller.log 2>&1 &
controller_pid=$!
cleanup() {
  kill "$scan_pid" "$controller_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
python3 -m p2b_backend_ros.node --config /config/p2b_backend_ros.two_goal.resolved.json --run-id cpu-preflight --run-epoch-ns 123456789 --applied-snapshot /preflight/current_command.json --finish-request /preflight/finish_request.json --pct-port 47631 --http-port 8765
"""


def remote_script() -> str:
    return r'''#!/usr/bin/env python3
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
'''


def package_for_preflight(local_run: Path) -> None:
    scripts = local_run / "scripts"
    scripts.mkdir(exist_ok=True)
    (scripts / "backend_start_cpu_preflight.sh").write_text(render_backend_script(), encoding="utf-8")
    (scripts / "remote_cpu_preflight.py").write_text(remote_script(), encoding="utf-8")
    (scripts / "backend_start_cpu_preflight.sh").chmod(0o755)
    (scripts / "remote_cpu_preflight.py").chmod(0o755)
    resolved = local_run / "config/p2b_backend_ros.two_goal.resolved.json"
    if not resolved.exists():
        base = local_run / "config/p2b_backend_ros.two_goal.json"
        cfg = json.loads(base.read_text(encoding="utf-8"))
        cfg["run_epoch_ns"] = 123456789
        cfg["applied_evidence"]["current_command_path"] = "/preflight/current_command.json"
        cfg["applied_evidence"]["finish_request_path"] = "/preflight/finish_request.json"
        write_json(resolved, cfg)


def run_command(label: str, command: List[str], log_path: Path, timeout: int = 600) -> None:
    p = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(p.stdout, encoding="utf-8")
    if p.returncode:
        raise RuntimeError("%s failed exit=%s tail=%s" % (label, p.returncode, p.stdout[-2000:]))


def execute(args) -> Path:
    local_run = Path(args.local_run).resolve()
    package_for_preflight(local_run)
    run_id = args.run_id or (local_run.name + "_cpu_preflight")
    remote_run = args.remote_root.rstrip("/") + "/" + run_id
    commands = {
        "remote_run": remote_run,
        "mkdir": ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", args.host, "python3 -c " + shlex.quote("from pathlib import Path; p=Path(%r); assert not p.exists(), p; p.mkdir(parents=True)" % remote_run)],
        "sync": ["rsync", "-a", "--delete", str(local_run) + "/", f"{args.host}:{remote_run}/"],
        "run": ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", args.host, shlex.join(["python3", remote_run + "/scripts/remote_cpu_preflight.py", "--run-root", remote_run, "--foxy-image-id", FOXY_IMAGE_ID, "--remote-scan-workspace", args.remote_scan_workspace])],
        "collect": ["rsync", "-a", f"{args.host}:{remote_run}/artifacts/", str(local_run / "cpu_preflight_returned_artifacts") + "/"],
    }
    write_json(local_run / "cpu_preflight_commands.json", commands)
    logs = local_run / "cpu_preflight_host_logs"
    started = False
    original_error = None
    collect_error = None
    verdict = {"remote_started": False}
    try:
        run_command("mkdir", commands["mkdir"], logs / "00_mkdir.log")
        run_command("sync", commands["sync"], logs / "01_sync.log")
        started = True
        verdict["remote_started"] = True
        run_command("run", commands["run"], logs / "02_run.log", timeout=300)
    except Exception as exc:
        original_error = exc
        verdict["run_error"] = str(exc)
    finally:
        if started:
            try:
                run_command("collect", commands["collect"], logs / "03_collect.log")
                ret = local_run / "cpu_preflight_returned_artifacts"
                expected = json.loads((ret / "cpu_preflight_artifact_hashes.json").read_text(encoding="utf-8"))
                actual = {p.relative_to(ret).as_posix(): sha256(p) for p in ret.rglob("*") if p.is_file() and p.name != "cpu_preflight_artifact_hashes.json"}
                exp = {k: v for k, v in expected.items() if k != "cpu_preflight_artifact_hashes.json"}
                verdict.update({"returned_hashes_match": actual == exp, "actual_count": len(actual), "expected_count": len(exp)})
            except Exception as exc:
                collect_error = exc
                verdict["collect_error"] = str(exc)
    write_json(local_run / "cpu_preflight_return_verdict.json", verdict)
    if original_error is not None:
        if collect_error is not None:
            raise RuntimeError("preflight failed and collect failed: %s / %s" % (original_error, collect_error)) from original_error
        raise original_error
    if collect_error is not None:
        raise collect_error
    if not verdict.get("returned_hashes_match"):
        raise RuntimeError("returned hashes mismatch")
    return local_run


def build_parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--local-run", required=True)
    p.add_argument("--run-id")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--host", default="gpu5070ti")
    p.add_argument("--remote-root", default=DEFAULT_REMOTE_ROOT)
    p.add_argument("--remote-scan-workspace", default=DEFAULT_REMOTE_SCAN)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    local_run = Path(args.local_run).resolve()
    package_for_preflight(local_run)
    if args.execute:
        local_run = execute(args)
    print(json.dumps({"local_run": str(local_run), "execute": bool(args.execute), "commands": str(local_run / "cpu_preflight_commands.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
