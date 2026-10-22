"""Compare the actual current ground classifier to the qualified floor source."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import os
import subprocess

R=Path('/home/ubuntu/sun/vla_v290_20261021')
P=Path('/home/ubuntu/sun/vla_v289_20261020')
IMAGE='sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert json.loads((R/'evidence/evaluators01.json').read_text())['checks'][0]['returncode']==0
    tag=os.environ.get('V290_CLASSIFICATION_ID','01')
    results=dict(physics_steps=0,cases=[],checks=[])
    for case in ['build','A04','G05','CU06','CM02']:
        shell='cmake --build /evaluation/build -j2 --target classification_probe' if case=='build' else (
            f'CLASSIFICATION_INPUT=/input/{case}/contributor_points.txt CLASSIFICATION_OUTPUT=/output/{case}_classification.csv '
            f'/evaluation/build/classification_probe --ros-args --params-file /input/{case}/profile.yaml --log-level error')
        cmd=['docker','run','--rm','--pull=never','--name','v290-classification-'+tag+'-'+case,'--user',f'{os.getuid()}:{os.getgid()}',
            '--cpus=2','--memory=6g','--network=host','-e','ROS_HOME=/evaluation/ros_home','-e','ROS_LOG_DIR=/evaluation/ros_logs',
            '-v',str(R/'native')+':/work:ro','-v',str(P/'native/fixtures')+':/work/fixtures:ro',
            '-v',str(P)+':/parent:ro','-v',str(R/'source')+':/source:ro',
            '-v',str(R/'evaluation')+':/evaluation:rw','-v',str(R/'captured')+':/input:ro',
            '-v',str(R/'captured_results')+':/output:rw','--entrypoint','/bin/bash',IMAGE,'-c',
            'source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && export ROS_DOMAIN_ID=158 ROS_LOCALHOST_ONLY=1 && '+shell]
        log=R/f'evidence/classification{tag}_{case}.log'
        with log.open('x') as stream:code=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT).returncode
        results['checks'].append(dict(case=case,returncode=code,log_sha256=sha(log)))
        if code:raise SystemExit(code)
        if case=='build':continue
        p=R/f'captured_results/{case}_classification.csv';rows=list(csv.DictReader(p.open()))
        counts=Counter((x['current_ground'],x['physical_height_match']) for x in rows)
        bad=[x for x in rows if x['current_ground']=='0']
        results['cases'].append(dict(case_id=case,points=len(rows),counts={str(k):v for k,v in counts.items()},
            first_nonterrain=bad[:12],csv_sha256=sha(p)))
    (R/f'evidence/classification{tag}.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':main()
