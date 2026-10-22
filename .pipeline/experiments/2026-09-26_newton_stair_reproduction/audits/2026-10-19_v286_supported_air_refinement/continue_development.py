"""Close exact parent comparison, then remaining candidate checks; no scoring."""
from pathlib import Path
import json,os,subprocess,time
HERE=Path(__file__).resolve().parent;V=HERE.parents[1]/'versions/v286'
ROOT=Path('/home/sun/vla_exec/supported_air_refinement_v286')
receipt=ROOT/'development_continuation02.json';assert not receipt.exists()
row=dict(started_utc_s=time.time(),physics_steps=0,stage='parent_probe02',checks=[])
receipt.write_text(json.dumps(row,indent=2)+'\n')
steps=[('parent_probe02',HERE/'parent_probe.py',dict(V286_PARENT_ID='02')),
       ('reuse_cohort01',V/'reuse_cohort.py',{}),
       ('candidate_native02',HERE/'develop.py',dict(V286_DEVELOP_ID='02',V286_REUSE_BUILD_ID='01'))]
for label,source,environment in steps:
    with (ROOT/(label+'_continuation.log')).open('x') as log:
        code=subprocess.run(['python3',str(source)],env=dict(os.environ,**environment),stdout=log,stderr=subprocess.STDOUT).returncode
    row['checks'].append(dict(label=label,returncode=code));row['stage']=label
    receipt.write_text(json.dumps(row,indent=2)+'\n')
    assert code==0,(label,code)
assert json.loads((ROOT/'development02.json').read_text())['stage']=='passed'
row.update(stage='ready_for_qualification_review',finished_utc_s=time.time(),returncode=0)
receipt.write_text(json.dumps(row,indent=2)+'\n')
