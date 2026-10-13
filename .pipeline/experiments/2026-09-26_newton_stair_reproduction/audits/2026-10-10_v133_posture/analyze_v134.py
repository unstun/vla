"""Read every closed v134 pilot; separate route rejection from body failure."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];TASK=Path('/data/sun/vla_mppi_20261009')
sys.path.insert(0,str(BASE/'versions/v127'))
from analyze_remote import Capture
def main():
    out=TASK/'results/v133_posture/v134_diagnosis.json';assert not out.exists()
    cases=[]
    for i in range(1,4):
        tag=f'v134_candidate_attempt{i:02d}';c=Capture(TASK/'trials'/tag/'runs'/tag)
        lines=c.read('nav2.log').splitlines();events=c.rows('artifacts/reactive_observations.jsonl')
        routes=[e for e in events if e['event']=='pct_route']
        telemetry=c.rows('telemetry.jsonl')
        case={'run':tag,'admissions':[l for l in lines if 'V132_REFERENCE_ADMISSION' in l],
              'stops':[l for l in lines if 'SCAN output revoked' in l or 'SCAN evidence rejected now=' in l],
              'collision_examples':[l for l in lines if 'initial_spline_collision' in l][:5],
              'reason_examples':[l for l in lines if 'reason=' in l and any(x in l for x in ['target','spline','reference'])][-12:],
              'final_pose':telemetry[-1]['body_sensor'],
              'minimum_base_up_z':min(r['base_up_z'] for r in telemetry),
              'routes':[{'generation':e['data']['generation'],'time_s':e['clock_ns']/1e9,
                         'points':[[p['pose']['position'][k] for k in ['x','y','z']] for p in e['data']['path']['poses']]} for e in routes],
              'sources':c.sources}
        cases.append(case)
    report={'cases':cases,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    out.write_text(json.dumps(report,indent=2)+'\n')
    for c in cases:print(json.dumps({k:v for k,v in c.items() if k not in ['sources','routes']}))
if __name__=='__main__':main()
