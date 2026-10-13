"""Build actual-install replays, then alternate timing arms on identical input."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import statistics
import subprocess

HERE=Path(__file__).resolve().parent
TASK=Path('/data/sun/vla_mppi_20261009')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',type=int,required=True);args=parser.parse_args()
    assert json.loads((TASK/'results/step3_repeats/progress.json').read_text())['state']=='completed'
    output=TASK/f'results/step3_repeats/replay{args.attempt:02d}';output.mkdir(exist_ok=False);(output/'ros_logs').mkdir()
    inputs=TASK/'step3_repeats_replay/input';identity=json.loads((inputs/'identity.json').read_text())
    for name,expected in identity['input_sha256'].items():assert sha(inputs/name)==expected
    image=json.loads((TASK/'results/step3_v127/candidate_receipt.json').read_text())['image_id']
    remote=lambda p:'/task/'+str(p.relative_to(TASK))
    source='/repo/'+str(HERE.relative_to(TASK/'repo'))
    def run(script,log,record_dir):
        cmd=['docker','run','--rm','--network=none','--cpus=4','--memory=8g',
            '-e','ROS_DOMAIN_ID=196','-e','ROS_LOCALHOST_ONLY=1',
            '-e','ROS_LOG_DIR='+remote(output/'ros_logs'),
            '-e','REPLAY_INPUT='+remote(inputs),'-e','REPLAY_OUTPUT='+remote(record_dir),
            '-v',f'{TASK}:/task:rw','-v',f'{TASK}/repo:/repo:ro',
            '--entrypoint','/bin/bash',image,'-c',script]
        with log.open('w') as stream:
            subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=600)
    build={};setups={}
    for variant,workspace in [('baseline','candidate'),('candidate','step3_v127')]:
        build[variant]=remote(output/f'build_{variant}')
        setups[variant]='set -eo pipefail\nsource /opt/ros/foxy/setup.bash\n'+f'source /task/{workspace}/install/setup.bash\n'
        script=setups[variant]+f'cmake -S {source} -B {build[variant]} -DCMAKE_BUILD_TYPE=Release -DNATIVE_WORKSPACE=/task/{workspace} -DVERSIONS_ROOT={source}/../../../versions -DCANDIDATE={"ON" if variant=="candidate" else "OFF"}\n'+f'cmake --build {build[variant]} -j2\n'
        run(script,output/f'{variant}_build.log',output)
    # Alternate the same complete curve corpus; logging muted identically.
    timing={v:[] for v in build};hashes={};runs=[]
    for sequence,variant in enumerate(('baseline','candidate','candidate','baseline','baseline','candidate')):
        directory=output/f'numeric_{sequence}_{variant}';directory.mkdir()
        run(setups[variant]+build[variant]+'/curve_replay --ros-args --log-level error',output/f'numeric_{sequence}_{variant}.log',directory)
        report=json.loads((directory/'numeric.json').read_text());assert report['curves']==identity['candidate_curves']
        assert report['epochs']==identity['epochs']
        pair={name:sha(directory/name) for name in ('curves.csv','epochs.csv')}
        if hashes:assert pair==hashes,'Recorded native verdict mismatch'
        else:hashes=pair
        timing[variant].append(report['validation_us_mean']);runs.append({'sequence':sequence,'variant':variant,**report})
    map_hashes={};map_rows={}
    for variant in build:
        directory=output/f'map_{variant}';directory.mkdir()
        run(setups[variant]+build[variant]+'/map_replay --ros-args --params-file '+source+'/../../../versions/v127/building_planner.yaml --log-level error',output/f'map_{variant}.log',directory)
        map_hashes[variant]=sha(directory/'maps.tsv')
        map_rows[variant]=(directory/'maps.tsv').read_text().splitlines()
    assert map_hashes['baseline']==map_hashes['candidate'],'Reconstructed map/query verdict differs'
    result={'passed':True,'candidate_curves':identity['candidate_curves'],'epochs':identity['epochs'],
            'numeric_verdict_hashes':hashes,'numeric_runs':runs,'mean_validation_us_median_of_three':{v:statistics.median(xs) for v,xs in timing.items()},
            'map_query_rows':len(map_rows['baseline']),'map_hashes':map_hashes,'map_rows':map_rows['baseline'],
            'input_identity_sha256':sha(inputs/'identity.json'),'source_sha256':{p.name:sha(p) for p in HERE.iterdir() if p.is_file()},
            'limits':['Numeric curves/seed controls are original 17-digit captured values.',
                      'Map prefixes are reconstructed in ordered replay, not restored live asynchronous map revisions.',
                      'Logged rejected phase has six decimal digits; query body is the last recorded body at/before the chosen clock.',
                      '249/251 ms cases are explicit clock counterfactuals; no runtime threshold is changed.',
                      'Isolated numeric timing is not full physics or controller deadline qualification.']}
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('map_rows','source_sha256')},indent=2),flush=True)
if __name__=='__main__':main()
