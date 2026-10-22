from pathlib import Path
import os,subprocess
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'generic_mechanisms_v249/late_pose_recheck01';OUT.mkdir(parents=True,exist_ok=False)
source='/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-18_v249_generic_mechanism_repairs'
shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /task/callback_failure_v232/install/setup.bash && source /task/cooperative_search_v240/install/setup.bash && source /task/physical_traversability_v247/native/install/setup.bash && source /work/install/setup.bash'
shell+=' && cmake -S '+source+' -B /output/build && cmake --build /output/build --target pose_recheck -j2 && /output/build/pose_recheck /task/generic_mechanisms_v249/late_global_baseline01/results/rejected_poses.csv /output/poses.csv'
shell+=' && /output/build/pose_recheck '+source+'/a02_recorded_poses.csv /output/a02_poses.csv'
raise SystemExit(subprocess.run(['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
 '--cpus=2','--memory=6g','-v',str(BASE)+':/task:ro','-v',str(BASE/'generic_mechanisms_v251/native')+':/work:ro',
 '-v',str(OUT)+':/output:rw','--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',shell]).returncode)
