"""Run actual retry-flow and real recorded-input regressions on exact installs."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

TASK=Path('/data/sun/vla_mppi_20261009')
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--attempt',type=int,required=True)
    args=parser.parse_args()
    output=TASK/f'results/step2_v126/contracts{args.attempt:02d}'
    output.mkdir(exist_ok=False)
    (output/'ros_logs').mkdir()
    fixture=output/'fixture'
    subprocess.run(['python3',str(HERE/'prepare_retry_harness.py'),str(TASK/'candidate'),
                    str(TASK/'step2_v126'),str(fixture),str(output/'transformation.json')],check=True)
    image=json.loads((TASK/'results/step2_v126/candidate_receipt.json').read_text())['image_id']
    remote=lambda p:'/task/'+str(p.relative_to(TASK))
    source='/repo/'+str(HERE.relative_to(TASK/'repo'))
    script='\n'.join(['set -eo pipefail','source /opt/ros/foxy/setup.bash',
        'source /task/candidate/install/setup.bash',
        f'cmake -S {source} -B {remote(output)}/build -DCMAKE_BUILD_TYPE=Release -DFIXTURE_ROOT={remote(fixture)}',
        f'cmake --build {remote(output)}/build -j2',
        f'{remote(output)}/build/retry_parent --ros-args --params-file {source}/../../v114/building_planner.yaml',
        f'{remote(output)}/build/retry_candidate --ros-args --params-file {source}/../../v114/building_planner.yaml'])
    def docker(script,log):
        cmd=['docker','run','--rm','--network=none','--cpus=4','--memory=8g',
             '-e','ROS_DOMAIN_ID=195','-e','ROS_LOCALHOST_ONLY=1',
             '-e','ROS_LOG_DIR='+remote(output/'ros_logs'),'-e','V114_INPUT=/task/fixed_curve_input',
             '-v',f'{TASK}:/task:rw','-v',f'{TASK}/repo:/repo:ro',
             '--entrypoint','/bin/bash',image,'-c',script]
        with log.open('w') as stream:
            subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=300)
    docker(script,output/'retry.log')
    retry=(output/'retry.log').read_text()
    assert retry.count('V126_RETRY_PASSED')==2
    cases=[json.loads(line.split('V126_RETRY_CASE ',1)[1]) for line in retry.splitlines() if 'V126_RETRY_CASE ' in line]
    assert len(cases)==12 and all(x['passed'] for x in cases)
    curves={}
    curve_source='/repo/'+str((BASE/'audits/2026-10-09_mppi_incremental/curve_parity').relative_to(TASK/'repo'))
    for variant,install in (('baseline','candidate'),('candidate','step2_v126')):
        script='\n'.join(['set -eo pipefail','source /opt/ros/foxy/setup.bash',
            f'source /task/{install}/install/setup.bash',
            f'cmake -S {curve_source} -B {remote(output)}/curve_{variant} -DCMAKE_BUILD_TYPE=Release -DCANDIDATE=ON',
            f'cmake --build {remote(output)}/curve_{variant} -j2',
            f'{remote(output)}/curve_{variant}/curve_probe --ros-args --params-file {source}/../../v114/building_planner.yaml'])
        docker(script,output/f'curve_{variant}.log')
        text=(output/f'curve_{variant}.log').read_text()
        assert 'V114_PUBLICATION_PROOF_PASS' in text
        records=[json.loads(line.split('MPPI_CURVE ',1)[1]) for line in text.splitlines() if 'MPPI_CURVE ' in line]
        assert len(records)==1
        curves[variant]=records[0]
    assert curves['baseline']==curves['candidate'],'actual native curve differs'
    result={'passed':True,'retry_control_flow_cases':cases,'real_native_curve_bit_identical':True,
            'real_native_publication_and_stale_rejection_both_passed':True,
            'control_values':len(curves['baseline']['control_bits']),
            'fixture_identity_sha256':sha(TASK/'fixed_curve_input/identity.json'),
            'source_sha256':{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts},
            'logs':{p.name:sha(p) for p in output.glob('*.log')},'image_id':image}
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
