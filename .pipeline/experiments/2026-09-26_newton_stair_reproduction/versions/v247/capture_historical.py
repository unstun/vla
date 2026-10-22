"""Original endpoint component regression: fresh original-ray fixture, zero steps."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;EXP=HERE.parents[1]
OUT=Path('/data/sun/vla_mppi_20261009/physical_traversability_v247/historical')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original=EXP/'inputs/historical_full_building.json';scenario=json.loads(original.read_text())
folder=OUT/'cases/H00';folder.mkdir(parents=True,exist_ok=False)
p=folder/'scenario.json';p.write_bytes(original.read_bytes())
a=scenario['spawn_ground_xyz_m'];b=scenario['goal_ground_xyz_m'];yaw=scenario['spawn_yaw_rad']
(folder/'endpoints.txt').write_text(' '.join(map(str,a[:2]+[a[2]+.3]+b[:2]+[b[2]+.3,yaw]))+'\n')
case=dict(case_id='H00',start=dict(ground=a,yaw=yaw),goal=dict(ground=b,yaw=0),scenario_sha256=sha(p),direction='historical_ascent')
(OUT/'cases_manifest.json').write_text(json.dumps(dict(cases=[case],original_scenario_sha256=sha(original),calls_per_case=1),indent=2)+'\n')
parent=HERE.parent/'v242/capture_cases.py'
namespace=dict(__file__=str(parent),__name__='historical_capture')
exec(compile(parent.read_text(),str(parent),'exec'),namespace)
namespace['OUT']=OUT;namespace['main']()
