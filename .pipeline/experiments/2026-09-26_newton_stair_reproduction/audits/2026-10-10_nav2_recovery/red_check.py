"""Run the new callback regression against the unchanged pre-MPPI install."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
TASK = Path('/data/sun/vla_mppi_20261009')
parser = argparse.ArgumentParser()
parser.add_argument('--attempt', type=int, required=True)
args = parser.parse_args()
OUT = TASK / f'results/recovery_red{args.attempt:02d}'
assert json.loads((TASK / 'results/recovery_original_v114/progress.json').read_text())['state'] == 'completed'
assert not subprocess.check_output(['docker', 'ps', '-q'], text=True).strip()
OUT.mkdir(exist_ok=False)
(OUT / 'ros_logs').mkdir()
source = '/repo/' + str(HERE.relative_to(TASK / 'repo'))
version = source + '/../../versions/v128'
image = json.loads((TASK / 'results/baseline_receipt.json').read_text())['image_id']
script = f'''set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/baseline/install/setup.bash
cmake -S {source} -B /task/results/recovery_red01/build -DTEST_SOURCE={version}/src/scan_nav2_controller/test/test_controller.cpp -DNATIVE_WORKSPACE=/task/baseline
cmake --build /task/results/recovery_red01/build -j2
set +e
/task/results/recovery_red01/build/recovery_regression --gtest_filter='PluginTest.NegativeSafetyTriggersRecoveryOnNextTick:PluginTest.NegativeCandidateProofTriggersRecoveryInAdmissionTick' --gtest_output=xml:/task/results/recovery_red01/tests.xml
code=$?
test "$code" = 1
'''
script = script.replace('/task/results/recovery_red01', '/task/' + str(OUT.relative_to(TASK)))
(OUT / 'run.sh').write_text(script)
command = ['docker', 'run', '--rm', '--network=none', '--cpus=4', '--memory=8g',
           '-e', 'ROS_DOMAIN_ID=197', '-e', 'ROS_LOG_DIR=/task/' + str((OUT / 'ros_logs').relative_to(TASK)),
           '-v', f'{TASK}:/task:rw', '-v', f'{TASK}/repo:/repo:ro',
           '--entrypoint', '/bin/bash', image, '/task/' + str((OUT / 'run.sh').relative_to(TASK))]
with (OUT / 'run.log').open('w') as log:
    subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=240)
import xml.etree.ElementTree as ET
root = ET.parse(OUT / 'tests.xml').getroot()
assert int(root.attrib['tests']) == 2 and int(root.attrib['failures']) == 2
failures = [node.text for node in root.iter('failure')]
assert all('throws an exception' in text for text in failures), failures
report = {'baseline': 'v114', 'tests': 2, 'expected_failed_tests': 2,
          'failed_assertions': failures, 'callback_gap_reproduced': True,
          'source_sha256': hashlib.sha256((HERE.parents[1] / 'versions/v128/src/scan_nav2_controller/test/test_controller.cpp').read_bytes()).hexdigest()}
(OUT / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
