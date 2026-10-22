"""Real native down/up Search to the same admitted downstairs grid point."""
from pathlib import Path
import os,subprocess,numpy as np,json
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'endpoint_connectivity_v244/diagnostic'
if __name__=='__main__':
    nl,nx,ny,res,cx,cy=map(float,(OUT/'graph_meta.txt').read_text().split());nl,nx,ny=int(nl),int(nx),int(ny)
    a=np.fromfile(OUT/'graph_states.f64',dtype='<f8').reshape(nl,nx,ny,6)
    v=np.loadtxt(OUT/'visited_R11.csv',delimiter=',',dtype=int).reshape(-1,3)
    candidates=[]
    for k,x,y in v:
        if k==0 and a[k,x,y,0]<=20 and a[k,x,y,5] and abs(a[k,x,y,1]-.05804443359375)<.02:
            p=np.array([(x-nx//2)*res+cx,(y-ny//2)*res+cy,a[k,x,y,1]+.3]);candidates.append(p)
    target=min(candidates,key=lambda p:np.linalg.norm(p[:2]-[-5.545314789,6.013188839]))
    origin=np.array([-1.045314789,2.513188839,4.833031197])
    control=OUT/'down_control';control.mkdir(exist_ok=True)
    (control/'endpoints.txt').write_text(' '.join(map(str,np.r_[origin,target]))+'\n')
    shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /task/callback_failure_v232/install/setup.bash && source /work/install/setup.bash'
    shell+=' && /observer/build/graph_dump /observer/down_control/endpoints.txt > /evaluation/search.log'
    subprocess.run(['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
     '--cpus=6','--memory=6g','-v',str(BASE)+':/task:ro','-v',str(BASE/'cooperative_search_v240')+':/work:ro',
     '-v',str(BASE/'callback_failure_v232/fixtures')+':/work/fixtures:ro','-v',str(OUT)+':/observer:ro',
     '-v',str(control)+':/evaluation:rw','--entrypoint','/bin/bash',
     'sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',shell],check=True)
    print((control/'search.log').read_text())
