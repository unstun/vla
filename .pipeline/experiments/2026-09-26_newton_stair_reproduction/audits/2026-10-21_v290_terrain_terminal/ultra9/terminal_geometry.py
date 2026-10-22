"""Static goal-center yaw sweep; diagnostic geometry only, not a motion/run."""
from pathlib import Path
import csv,hashlib,json,math,os,subprocess
R=Path('/home/ubuntu/sun/vla_v290_20261021')
E=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
A=E/'audits/2026-10-21_v290_terrain_terminal'
O=R/'terminal_geometry01'
def main():
    O.mkdir(exist_ok=False)
    cohort=json.loads((R/'cohort/cases_manifest.json').read_text())
    ids=cohort['physical_cases'];mapping=[]
    with (O/'poses.txt').open('x') as stream:
        for cid in ids:
            case=next(c for c in cohort['cases'] if c['case_id']==cid)
            goal=case['goal']['ground'];yaw=case['goal']['yaw']
            for label,angle in [('requested_yaw',yaw)]+[(f'sweep_{i:02d}',-math.pi+i*math.pi/16) for i in range(32)]:
                index=len(mapping);mapping.append(dict(index=index,case_id=cid,label=label,yaw_rad=angle,
                    body_xyz=[goal[0],goal[1],goal[2]+.3]))
                stream.write(' '.join(map(str,[index,goal[0],goal[1],goal[2]+.3,angle]))+'\n')
    binary=A/'physical/A04/margin_build'
    assert (binary/'body_margin').exists()
    shell='source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && source /work/fixtures/probe271.env && /probe/body_margin /work/fixtures/building/environment225.env 10040917858432847476 /work/fixtures/building/native.support 15212154834549674106 /audit/poses.txt /audit/margins.csv $RAW_FIELD $RAW_FNV'
    cmd=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}','--cpus=1','--memory=3g','-v',str(R/'native')+':/work:ro','-v',str(binary)+':/probe:ro','-v',str(O)+':/audit:rw','--entrypoint','/bin/bash','sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343','-c',shell]
    subprocess.run(cmd,check=True)
    values=list(csv.DictReader((O/'margins.csv').open()));assert len(values)==len(mapping)
    for meta,row in zip(mapping,values):meta.update(source_solid_margin_m=float(row['native_source_solid_margin_m']),static_support_verdict=int(row['static_support_verdict']))
    summary=[]
    for cid in ids:
        part=[r for r in mapping if r['case_id']==cid];requested=part[0];sweep=part[1:]
        summary.append(dict(case_id=cid,requested=requested,minimum_yaw_sweep_source_margin_m=min(r['source_solid_margin_m'] for r in sweep),
            negative_yaw_samples=sum(r['source_solid_margin_m']<0 for r in sweep),worst=min(sweep,key=lambda r:r['source_solid_margin_m'])))
    (O/'summary.json').write_text(json.dumps(dict(physics_steps=0,scope='Static exact goal-center poses at nominal body clearance; synthetic yaw probes, not actual motion, not navigation inputs',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases=summary,queries=mapping),indent=2)+'\n')
    print(json.dumps(summary))
if __name__=='__main__':main()
