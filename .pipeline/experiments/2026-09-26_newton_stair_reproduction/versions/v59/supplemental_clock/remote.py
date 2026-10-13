"""Bounded actual-parent controller reproduction; no physics or source mutation."""
from pathlib import Path
import hashlib,json,subprocess,time,os
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[2]
assert str(BASE).startswith('/home/sun/vla_exec/vla/')
os.environ['PATH']='/home/sun/vla_exec/bin:'+os.environ['PATH']
out=HERE/'attempt01';out.mkdir(parents=True)
native=BASE/'runtime/scan80_trajectory_epoch_v59'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
command=['docker','run','--rm','--pull=never','--network=none','--name','vla-v59-supplemental-clock','--cpus=2','--memory=3g','-e','ROS_DOMAIN_ID=221','-e','ROS_LOCALHOST_ONLY=1','-v',str(native)+':/workspace:ro','-v',str(HERE)+':/contract:ro','-v',str(out)+':/attempt:rw','--entrypoint','/bin/bash','sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb','-c','source /opt/ros/humble/setup.bash && source /workspace/install/setup.bash && cmake -S /contract -B /attempt/build -DCMAKE_BUILD_TYPE=Release && cmake --build /attempt/build --target controller_epoch_probe -j2 && /attempt/build/controller_epoch_probe --ros-args -p use_sim_time:=true']
(out/'request.json').write_text(json.dumps({'command':command,'deadline_s':180,'probe_sha256':sha(HERE/'controller_epoch_probe.cpp'),'frozen_controller_sha256':sha(native/'src/plan_manage/src/closed_loop_controller.cpp'),'physics':False},indent=2)+'\n')
t=time.monotonic()
try:
 with (out/'execution.log').open('w') as log:code=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=180).returncode
finally:subprocess.run(['docker','rm','-f','vla-v59-supplemental-clock'],capture_output=True)
text=(out/'execution.log').read_text();passed=code==0 and 'V59_SUPPLEMENTAL_CLOCK_PASSED' in text
(out/'result.json').write_text(json.dumps({'passed':passed,'exit_code':code,'wall_s':time.monotonic()-t,'supplemental_clock_checks_passed':passed,'execution_log_sha256':sha(out/'execution.log')},indent=2)+'\n');print((out/'result.json').read_text());raise SystemExit(0 if passed else 1)
