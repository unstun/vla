"""Independent original raw-voxel comparison of actually recorded body poses."""
from pathlib import Path
import csv,hashlib,json,os,subprocess
HERE=Path(__file__).resolve().parent;EXP=HERE.parents[1];BASE=Path('/data/sun/vla_mppi_20261009')
OUT=BASE/'generalization_v248/raw_pose_audit01';OUT.mkdir(exist_ok=False)
source='/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-18_v247_physical_traversability'
shell='cmake -S '+source+'/raw_pose_probe -B /raw/build -DVERSIONS_ROOT='+str(EXP/'versions').replace(str(BASE),'/task')+' -DRAW_ARCHIVE=/task/physical_traversability_v247/evaluation/build/libraw_reference.a && cmake --build /raw/build -j2'
for cid in ('A02','G07','R11'):
 poses=str(HERE/'physical'/cid/'body_poses.txt').replace(str(BASE),'/task')
 shell+=' && /raw/build/raw_pose /task/environment_score_v224/fixtures/building/environment03.env 4316416882194453309 '+poses+' /raw/'+cid+'.csv'
cmd=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}','--cpus=4','--memory=4g','-v',str(BASE)+':/task:ro','-v',str(OUT)+':/raw:rw','--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',shell]
with (OUT/'build_and_run.log').open('x') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
summary={}
for cid in ('A02','G07','R11'):
 rows=list(csv.DictReader((OUT/(cid+'.csv')).open()));windows=json.loads((HERE/'physical'/cid/'results/window_audit.json').read_text())['windows'];values={}
 for name,w in windows.items():
  lo,hi=w['measured']['window_s'];part=[r for r in rows if lo<=float(r['time_s'])<hi]
  values[name]=dict(samples=len(part),minimum_raw_extra_edge_m=min((float(r['raw_edge_margin_m']) for r in part),default=None),minimum_raw_solid_margin_m=min((float(r['raw_solid_margin_m']) for r in part),default=None))
 summary[cid]=values
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result=dict(cases=summary,physics_steps=0,source='Original v224 raw point-cloud evaluator isolated through frozen v232 raw_reference wrapper',
 raw_voxel_padding_m=3**.5*.025,radius_m=.35,offset_m=.18,raw_field_fnv64='4316416882194453309',
 source_sha256=sha(Path(__file__)),raw_archive_sha256=sha(BASE/'physical_traversability_v247/evaluation/build/libraw_reference.a'),
 claim='Conservative point-representative margin comparison; negative is not by itself proof of mesh contact. Separate from live native admission and foot contact.')
(OUT/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
