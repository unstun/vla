"""Check every unchanged legal start with the frozen v286 native hard fields."""
from pathlib import Path
import csv,hashlib,json,os,subprocess,sys
HERE=Path(__file__).resolve().parent;V=HERE.parents[1]/'versions/v286'
ROOT=Path('/home/sun/vla_exec/supported_air_refinement_v286');OUT=ROOT/'all_start_verification'
sys.path.insert(0,str(V));from run_matrix import verify
native=verify();OUT.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((ROOT/'cohort/cases_manifest.json').read_text());cases=[c for c in m['cases'] if c['expected']=='admit'];assert len(cases)==50
with (OUT/'queries.txt').open('x') as f:
    for c in cases:
        p=c['start'];f.write(' '.join(map(str,[c['case_id'],*p['ground'][:2],p['ground'][2]+.3,p['yaw']]))+'\n')
shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /task/callback_failure_v232/install/setup.bash && source /task/cooperative_search_v240/install/setup.bash && source /task/physical_traversability_v247/native/install/setup.bash && source /work/install/setup.bash && source /work/fixtures/probe271.env && /evaluation/build/spawn_margin /audit/queries.txt /audit/margins.csv'
with (OUT/'stdout.log').open('x') as log:
    subprocess.run(['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
        '--cpus=2','--memory=6g','-v','/data/sun/vla_mppi_20261009:/task:ro',
        '-v',str(ROOT/'native')+':/work:ro','-v',str(ROOT/'evaluation')+':/evaluation:ro','-v',str(OUT)+':/audit:rw',
        '--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',shell],stdout=log,stderr=subprocess.STDOUT,check=True)
rows=list(csv.DictReader((OUT/'margins.csv').open()));assert len(rows)==50 and len({r['id'] for r in rows})==50
for c,r in zip(cases,rows):
    assert r['id']==c['case_id'] and int(r['support_verdict'])==0
    assert min(float(r['edge_margin']),float(r['solid_margin']))>=.10,r
    for k in ['support_verdict','edge_margin','solid_margin']:assert r[k]==c['start_admission'][k],(c['case_id'],k)
report=dict(passed=True,legal_starts=50,physics_steps=0,required_extra_margin_m=.10,
    minimum_support_gap_extra_m=min(float(r['edge_margin']) for r in rows),
    minimum_source_solid_extra_m=min(float(r['solid_margin']) for r in rows),
    byte_unchanged_frozen_cohort=True,native_manifest_sha256=sha(V/'native_manifest.json'),
    evaluator_sha256=sha(ROOT/'evaluation/build/spawn_margin'),audit_source_sha256=sha(Path(__file__)),
    files={p.name:sha(p) for p in OUT.iterdir() if p.is_file()})
(HERE/'results/all50_start_verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
