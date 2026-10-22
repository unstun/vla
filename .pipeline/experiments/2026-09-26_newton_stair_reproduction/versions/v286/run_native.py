"""Run v286 evaluation against an explicitly selected installed native source."""
from pathlib import Path
import argparse, os, subprocess

HERE=Path(__file__).resolve().parent
BASE=Path('/data/sun/vla_mppi_20261009')
ROOT=Path('/home/sun/vla_exec/supported_air_refinement_v286')
p=argparse.ArgumentParser();p.add_argument('--parent',action='store_true')
p.add_argument('mode',choices=('build','contract','case','unit','spawn','continuity','tracking-build','terrain','repair-build','repair'))
p.add_argument('case',nargs='?');p.add_argument('output',nargs='?');a=p.parse_args()
work=Path('/home/sun/vla_exec/local_search_tracking_v285/native') if a.parent else ROOT/'native'
out=ROOT/('parent_evaluation' if a.parent else 'evaluation');out.mkdir(parents=True,exist_ok=True)
shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /task/callback_failure_v232/install/setup.bash && source /task/cooperative_search_v240/install/setup.bash && source /task/physical_traversability_v247/native/install/setup.bash && source /work/install/setup.bash'
shell+=' && export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ROS_DOMAIN_ID=154 ROS_LOCALHOST_ONLY=1 REPLAY_INPUT=/work/fixtures/building PCT_INPUT=/work/fixtures/building/native_original.pct && source /work/fixtures/probe271.env'
if a.mode in ('build','tracking-build','repair-build'):
    shell+=' && cmake -S /source -B /evaluation/build -DVERSIONS_ROOT=/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions -DCMAKE_BUILD_TYPE=Release && cmake --build /evaluation/build -j2'
    if a.mode=='repair-build':shell=shell.replace('cmake --build /evaluation/build -j2','cmake --build /evaluation/build --target repair_probe -j2')
    if a.mode=='tracking-build':shell=shell.replace('cmake --build /evaluation/build -j2','cmake --build /evaluation/build --target continuity_probe -j2')
elif a.mode=='contract':
    shell+=' && /evaluation/build/geometry_contract_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level warn'
elif a.mode=='repair':
    shell+=' && /evaluation/build/repair_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level warn'
elif a.mode=='terrain':
    shell+=' && /evaluation/build/terrain_search_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level warn'
elif a.mode=='continuity':
    shell+=' && /evaluation/build/continuity_probe'+(' --tracking-only' if a.parent else '')
elif a.mode=='unit':
    shell+=' && export ROUTE_ORACLE=/work/fixtures/route-oracle.yaml PCT_TEST_MAP=/work/fixtures/flat.pct && cd /work/build/lite3_nav2_plugins && ctest --output-on-failure'
elif a.mode=='spawn':
    shell+=' && /evaluation/build/spawn_margin /cohort/queries.txt /cohort/margins.csv'
else:
    if not a.case or not a.output: p.error('case mode requires input and output directories')
    case=Path(a.case).resolve();result=Path(a.output).resolve();result.mkdir(parents=True,exist_ok=True)
    if (result/'metrics.txt').exists():raise RuntimeError('Existing native result; never overwrite a scored call')
    shell+=' && export CASE_INPUT=/case PROBE_OUTPUT=/result STATIC_SUPPORT_INPUT=/work/fixtures/building/native.support STATIC_SUPPORT_FNV=15212154834549674106 && /evaluation/build/native_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level info'
command=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
    '--cpus=2','--memory=6g','--network=host','-e','ROS_HOME=/evaluation/ros_home','-e','ROS_LOG_DIR=/evaluation/ros_logs',
    '-v',str(BASE)+':/task:ro','-v',str(work)+(':/work:rw' if a.mode=='unit' else ':/work:ro'),
    '-v',str(HERE)+':/source:ro','-v',str(out)+':/evaluation:rw']
if a.mode=='case':command+=['--name','v286-case-'+case.name.lower(),'-v',str(case)+':/case:ro','-v',str(result)+':/result:rw']
if a.mode=='spawn':command+=['-v',str(ROOT/'cohort')+':/cohort:rw']
command+=['--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',shell]
raise SystemExit(subprocess.run(command).returncode)
