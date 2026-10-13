"""Compare original native checks and independent validator on exact installs."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

TASK=Path('/data/sun/vla_mppi_20261009')
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',type=int,required=True);args=parser.parse_args()
    output=TASK/f'results/step3_v127/contracts{args.attempt:02d}'
    output.mkdir(exist_ok=False);(output/'ros_logs').mkdir()
    source='/repo/'+str(HERE.relative_to(TASK/'repo'))
    relative=lambda p:'/task/'+str(p.relative_to(TASK))
    image=json.loads((TASK/'results/step3_v127/candidate_receipt.json').read_text())['image_id']
    records={}
    for variant,workspace in (('baseline','candidate'),('candidate','step3_v127')):
        record_dir=output/f'{variant}_records';record_dir.mkdir()
        build=relative(output/f'build_{variant}')
        script='\n'.join(['set -eo pipefail','source /opt/ros/foxy/setup.bash',
            f'source /task/{workspace}/install/setup.bash',
            f'cmake -S {source} -B {build} -DCMAKE_BUILD_TYPE=Release '+
            f'-DCANDIDATE={"ON" if variant=="candidate" else "OFF"} '+
            f'-DNATIVE_WORKSPACE=/task/{workspace} -DVERSIONS_ROOT={source}/../..',
            f'cmake --build {build} -j2',f'{build}/validation_probe',
            f'{build}/curve_probe --ros-args --params-file {source}/../../v114/building_planner.yaml',
            f'{build}/query_view_probe --ros-args --params-file {source}/../../v114/building_planner.yaml -p grid_map.asynchronous_mapping:=false'])
        command=['docker','run','--rm','--network=none','--cpus=4','--memory=8g',
                 '-e','ROS_DOMAIN_ID=195','-e','ROS_LOCALHOST_ONLY=1',
                 '-e','V127_RECORD_DIR='+relative(record_dir),
                 '-e','ROS_LOG_DIR='+relative(output/'ros_logs'),'-e','V114_INPUT=/task/fixed_curve_input',
                 '-v',f'{TASK}:/task:rw','-v',f'{TASK}/repo:/repo:ro',
                 '--entrypoint','/bin/bash',image,'-c',script]
        with (output/f'{variant}.log').open('w') as stream:
            subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=300)
        text=(output/f'{variant}.log').read_text()
        for marker in ('V127_VALIDATION_PASS','V114_PUBLICATION_PROOF_PASS','V114_QUERY_VIEW_PASS'):assert marker in text,marker
        records[variant]={prefix:[json.loads(line) for line in (record_dir/(prefix+'.jsonl')).read_text().splitlines() if line.strip()]
                          for prefix in ('V127_CHECK','V127_COLLISION','MPPI_CURVE')}
        assert len(records[variant]['V127_CHECK'])==341
        assert len(records[variant]['V127_COLLISION'])==35
        assert len(records[variant]['MPPI_CURVE'])==1
    assert records['baseline']==records['candidate'],'native verdict/curve parity differs'
    result={'passed':True,'native_versions':{'baseline':'v122','candidate':'v127'},
            'check_parity_cases':341,'real_map_collision_parity_cases':35,
            'successful_curve_bit_identical':True,'publication_and_stale_rejection_passed_both':True,
            'controller_snapshot_clock_pose_map_fault_publication_pin_checks_passed_both':True,
            'source_sha256':{p.name:sha(p) for p in HERE.iterdir() if p.is_file()},
            'logs':{p.name:sha(p) for p in output.glob('*.log')},'image_id':image,
            'record_files':{str(p.relative_to(output)):sha(p) for p in output.glob('*_records/*.jsonl')},
            'fixture_sha256':sha(TASK/'fixed_curve_input/identity.json'),'records':records['candidate']}
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='records'}),flush=True)
if __name__=='__main__':main()
