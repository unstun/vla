"""Probe native support on both floors; soft solid is a diagnostic column."""
from pathlib import Path
import os,subprocess,numpy as np
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'endpoint_connectivity_v244/diagnostic'
if __name__=='__main__':
    l,nx,ny,res,cx,cy=map(float,(OUT/'graph_meta.txt').read_text().split());l,nx,ny=int(l),int(nx),int(ny)
    a=np.fromfile(OUT/'graph_states.f64',dtype='<f8').reshape(l,nx,ny,6)
    with (OUT/'support_poses.txt').open('w') as f:
        for k,h in ((0,.05804443359375),(7,4.53125)):
            for x,y in zip(*np.nonzero((a[k,:,:,5]>0)&(np.abs(a[k,:,:,1]-h)<.2))):
                for heading in range(4):
                    f.write(f'{k}_{x}_{y}_{heading} {(x-nx//2)*res+cx:.17g} {(y-ny//2)*res+cy:.17g} {a[k,x,y,1]+.3:.17g} {heading*np.pi/4:.17g}\n')
    shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /task/callback_failure_v232/install/setup.bash && source /work/install/setup.bash'
    shell+=' && source /task/callback_failure_v232/fixtures/probe225.env'
    shell+=' && export SCREEN_POSES=/evaluation/support_poses.txt CASE_INPUT=/evaluation PROBE_OUTPUT=/evaluation/support_grid REPLAY_INPUT=/work/fixtures/building'
    shell+=' && /task/generalization_v242/build/native_probe --ros-args --params-file /work/fixtures/environment_candidate228.scan.yaml --log-level warn'
    subprocess.run(['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
    '--cpus=6','--memory=6g','-e','ROS_HOME=/evaluation/ros_home','-e','ROS_LOG_DIR=/evaluation/ros_logs',
    '-v',str(BASE)+':/task:ro','-v',str(BASE/'cooperative_search_v240')+':/work:ro',
    '-v',str(BASE/'callback_failure_v232/fixtures')+':/work/fixtures:ro','-v',str(OUT)+':/evaluation:rw',
    '--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',shell],check=True)
