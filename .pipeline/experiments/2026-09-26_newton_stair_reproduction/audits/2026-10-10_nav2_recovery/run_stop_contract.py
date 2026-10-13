"""Compare real gateway and BT waiting behavior around recorded 5.27-second stop."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
TASK = Path('/data/sun/vla_mppi_20261009')
BASE = HERE.parents[1]
sys.path.insert(0, str(BASE / 'versions/v127'))
from analyze_remote import Capture


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=('parent', 'candidate'), required=True)
    args = parser.parse_args()
    root = TASK / 'results/recovery_stop_contract'
    root.mkdir(exist_ok=True)
    fixture = root / 'input.json'
    if not fixture.exists():
        tag = 'v128_candidate_attempt04'
        capture = Capture(TASK / 'trials' / tag / 'runs' / tag)
        rows = capture.rows('artifacts/reactive_observations.jsonl')
        event = next(r for r in rows if r['event'] == 'scan_cancel')
        start = event['wall_monotonic_ns']
        sent = capture.rows('applied_sent.jsonl')
        config = capture.json('backend_config.json')['applied_evidence']
        data = {'run': tag, 'epoch': capture.json('episode_request.json')['run_epoch_ns'],
                'cancel_receipt_monotonic_ns': start,
                'samples': [r for r in sent if start - 50000000 <= r['ack']['linux_receive_ns'] <= start + 8000000000],
                'config': {k: config[k] for k in ('stop_command_norm', 'stop_speed_mps', 'stop_yaw_rate_radps', 'stop_dwell_sim_seconds')},
                'source': capture.sources}
        fixture.write_text(json.dumps(data, separators=(',', ':')) + '\n')
    out = root / args.variant
    out.mkdir(exist_ok=False)
    (out / 'ros_logs').mkdir()
    workspace = 'recovery_v128' if args.variant == 'parent' else 'recovery_v129'
    receipt = json.loads((TASK / 'results' / workspace / 'candidate_receipt.json').read_text())
    remote = lambda p: '/task/' + str(p.relative_to(TASK))
    source = '/repo/' + str(HERE.relative_to(TASK / 'repo'))
    script = f'''set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/{workspace}/install/setup.bash
cmake -S {source}/stop_contract -B {remote(out)}/build
cmake --build {remote(out)}/build -j2
set +e
{remote(out)}/build/stop_transport /task/{workspace}/install/lite3_nav2_plugins/lib/liblite3_bind_route_bt_node.so
code=$?
set -e
test "$code" = {1 if args.variant == 'parent' else 0}
python3 {source}/stop_wait_probe.py --input {remote(fixture)} --output {remote(out)}/gateway.json
'''
    (out / 'run.sh').write_text(script)
    command = ['docker', 'run', '--rm', '--network=none', '--cpus=4', '--memory=8g',
               '-e', 'ROS_DOMAIN_ID=199', '-e', 'ROS_LOG_DIR=' + remote(out / 'ros_logs'),
               '-e', 'PYTHONDONTWRITEBYTECODE=1', '-v', f'{TASK}:/task:rw',
               '-v', f'{TASK}/repo:/repo:ro', '--entrypoint', '/bin/bash', receipt['image_id'], remote(out / 'run.sh')]
    with (out / 'run.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
    report = json.loads((out / 'gateway.json').read_text())
    assert report['cases'][0]['success'] == (args.variant == 'candidate')
    transport = re.search(r'STOP_TRANSPORT success=(\d) elapsed_s=([\d.]+)', (out / 'run.log').read_text())
    assert transport and bool(int(transport[1])) == (args.variant == 'candidate')
    assert float(transport[2]) >= (5.2 if args.variant == 'candidate' else 4.9)
    result = {'passed': True, 'variant': args.variant, 'gateway': report,
              'transport_success': bool(int(transport[1])), 'transport_elapsed_s': float(transport[2]),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'Parent reproduces premature gateway/BT timeout; candidate must wait for proof. No physical acceptance.'}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
