"""Exercise installed Foxy recovery nodes with bounded synthetic failures."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
TASK = Path('/data/sun/vla_mppi_20261009')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', choices=('v130', 'v131'), required=True)
    parser.add_argument('--attempt', type=int, default=1)
    args = parser.parse_args()
    workspace = 'recovery_' + args.version
    root = TASK / 'results/recovery_retry_contract'
    out = root / f'{args.version}_{args.attempt:02d}'
    out.mkdir(parents=True, exist_ok=False)
    (out / 'ros_logs').mkdir()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    source_xml = TASK / workspace / 'install/lite3_nav2_bridge/share/lite3_nav2_bridge/config/navigate.xml'
    original = ET.fromstring(source_xml.read_text())
    recovery = original.find('./BehaviorTree/RecoveryNode')
    assert recovery is not None and [c.tag for c in recovery] == ['Sequence', 'WaitForScanStop']
    budget = int(recovery.attrib['number_of_retries'])
    assert budget == (2 if args.version == 'v130' else 6)
    recovery.remove(recovery[0])
    recovery.insert(0, ET.Element('NavigationFixture'))
    (out / 'fixture.xml').write_text(ET.tostring(original, encoding='unicode') + '\n')
    receipt = json.loads((TASK / 'results' / workspace / 'candidate_receipt.json').read_text())
    remote = lambda p: '/task/' + str(p.relative_to(TASK))
    source = '/repo/' + str(HERE.relative_to(TASK / 'repo'))
    script = f'''set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/{workspace}/install/setup.bash
cmake -S {source}/retry_contract -B {remote(out)}/build
cmake --build {remote(out)}/build -j2
{remote(out)}/build/retry_probe /opt/ros/foxy/lib/libnav2_recovery_node_bt_node.so /task/{workspace}/install/lite3_nav2_plugins/lib/liblite3_bind_route_bt_node.so {remote(out)}/fixture.xml {budget}
'''
    (out / 'run.sh').write_text(script)
    command = ['docker', 'run', '--rm', '--network=none', '--cpus=4', '--memory=8g',
               '-e', 'ROS_DOMAIN_ID=199', '-e', 'ROS_LOG_DIR=' + remote(out / 'ros_logs'),
               '-v', f'{TASK}:/task:rw', '-v', f'{TASK}/repo:/repo:ro',
               '--entrypoint', '/bin/bash', receipt['image_id'], remote(out / 'run.sh')]
    with (out / 'run.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
    lines = [line for line in (out / 'run.log').read_text().splitlines() if line.startswith('RETRY_CASE')]
    assert len(lines) == 3
    cases = [{k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', line)} for line in lines]
    assert all(c['passed'] and c['order_ok'] for c in cases)
    result = {'passed': True, 'version': args.version, 'budget': budget, 'cases': cases,
              'source_xml_sha256': sha(source_xml), 'fixture_xml_sha256': sha(out / 'fixture.xml'),
              'probe_sha256': sha(HERE / 'retry_contract/retry_probe.cpp'),
              'script_sha256': sha(Path(__file__)), 'image_id': receipt['image_id'],
              'scope': 'Actual installed RecoveryNode and WaitForScanStop; navigation and stop responses synthetic, not physical acceptance.'}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
