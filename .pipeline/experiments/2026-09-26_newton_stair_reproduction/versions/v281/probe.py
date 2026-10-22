"""Read-only frozen native/evaluator bindings; one named cold case container."""
from common import *
import os,subprocess,sys
def base_command(name):
    OUT.mkdir(parents=True,exist_ok=True)
    return ['docker','run','--rm','--pull=never','--name',name,
     '--user',f'{os.getuid()}:{os.getgid()}','--memory=6g','--cpus=2','--network=host',
     '-e','ROS_DOMAIN_ID=152','-e','ROS_HOME=/evaluation/ros_home','-e','ROS_LOG_DIR=/evaluation/ros_logs',
     '-v',str(BASE)+':/task:ro','-v',str(BASE/'source_physical_integration_v280/native')+':/work:ro',
     '-v',str(OUT)+':/evaluation:rw','-v',str(BASE/'source_physical_integration_v280/evaluation/build')+':/evaluation/build:ro',
     '--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4']

if __name__=='__main__':
    cohort,cid=sys.argv[1:];version,root,count=COHORTS[cohort]
    assert cid in {c['case_id'] for c in json.loads((HERE/(cohort+'.json')).read_text())['cases']}
    cmd=base_command('v281-'+cohort+'-'+cid.lower())+[
      '/task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v280/native.sh',
      '/task/'+root+'/cases/'+cid,'/evaluation/'+cohort+'/'+cid]
    raise SystemExit(subprocess.run(cmd).returncode)
