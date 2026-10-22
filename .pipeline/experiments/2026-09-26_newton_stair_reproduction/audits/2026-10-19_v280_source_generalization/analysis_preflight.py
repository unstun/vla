"""Compile the actual native measured-pose scorer and check frozen sample parity."""
from pathlib import Path
import csv,hashlib,json,os,subprocess
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'v282_analysis_preflight'
OUT.mkdir(exist_ok=True)
p=BASE/'source_integrated_benchmark_v281/clean50/A04/route_margins_native.csv'
rows=list(csv.DictReader(p.open()));chosen=[rows[i] for i in sorted({0,len(rows)//4,len(rows)//2,3*len(rows)//4,len(rows)-1})]
with (OUT/'sample_poses.txt').open('w') as f:
 for i,r in enumerate(chosen):f.write(' '.join([str(i*.1)]+[r[k] for k in ('x','y','z','yaw')])+'\n')
shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /work/install/setup.bash && source /work/fixtures/probe271.env'
shell+=' && cmake -S /source -B /audit/build -DCMAKE_BUILD_TYPE=Release && cmake --build /audit/build -j2'
shell+=' && /audit/build/body_margin /work/fixtures/building/environment225.env 10040917858432847476 /work/fixtures/building/native.support 15212154834549674106 /audit/sample_poses.txt /audit/body_margins.csv $RAW_FIELD $RAW_FNV'
with (OUT/'build01.log').open('x') as log:
 subprocess.run(['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=6g','-v',str(BASE)+':/task:ro','-v',str(BASE/'source_physical_integration_v280/native')+':/work:ro','-v',str(HERE)+':/source:ro','-v',str(OUT)+':/audit:rw','--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',shell],stdout=log,stderr=subprocess.STDOUT,check=True)
a=list(csv.DictReader((OUT/'body_margins.csv').open()));assert len(a)==len(chosen)
for r,old in zip(a,chosen):
 assert abs(float(r['native_source_solid_margin_m'])-float(old['native_solid_margin']))<1e-12
 assert abs(float(r['extra_edge_margin_m'])-float(old['edge_margin']))<1e-12
 assert r['static_support_free']=='1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=dict(passed=True,samples=len(a),source_sample_sha256=sha(p),physics_steps=0,planning_calls=0,source_margin_and_ENV_parity=True,
 source_files={n:sha(HERE/n) for n in ('CMakeLists.txt','body_margin.cpp','postprocess_case.py','analysis_preflight.py')})
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
