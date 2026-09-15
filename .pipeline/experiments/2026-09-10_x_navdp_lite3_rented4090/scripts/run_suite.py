"""Four bounded physical Lite3 point-goal trials with unchanged X-NavDP inference."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import queue
import random
import subprocess
import threading
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw
import torch

from runtime import EXP, Cameras, infer, load_mpc, load_policy, local_goal, robot

CASES = [
    {'id':'clear_1m','scene':'clear','distance_m':1.,'seed':41},
    {'id':'clear_2m','scene':'clear','distance_m':2.,'seed':42},
    {'id':'blocked_4m_seed41','scene':'blocked','distance_m':4.,'seed':41},
    {'id':'blocked_4m_seed42','scene':'blocked','distance_m':4.,'seed':42},
]

class Writer:
    def __init__(self, directory):
        self.directory=directory;self.queue=queue.Queue(40);self.error=None;self.count=0
        self.thread=threading.Thread(target=self.work,daemon=True);self.thread.start()

    def work(self):
        try:
            with (self.directory/'frames.jsonl').open('w',buffering=1) as stream:
                while True:
                    job=self.queue.get()
                    if job is None:return
                    array,metadata=job
                    filename=f'view_{self.count:05d}.jpg'
                    Image.fromarray(array).save(self.directory/filename,quality=92)
                    stream.write(json.dumps({**metadata,'file':filename})+'\n')
                    self.count+=1
        except BaseException as error:self.error=repr(error)

    def submit(self,array,metadata):
        if self.error:raise RuntimeError(self.error)
        self.queue.put_nowait((array,metadata))

    def close(self):
        if not self.error:self.queue.put(None,timeout=3)
        self.thread.join(timeout=15)
        if self.error or self.thread.is_alive():raise RuntimeError(self.error or 'Frame writer did not finish')

def montage(rgb,depth,chase,top,label):
    depth_color=cv2.applyColorMap((np.clip(depth/5,0,1)*255).astype(np.uint8),cv2.COLORMAP_TURBO)
    depth_color=cv2.cvtColor(depth_color,cv2.COLOR_BGR2RGB)
    panel=np.vstack([np.hstack([rgb,chase]),np.hstack([top,depth_color])])
    image=Image.fromarray(panel);draw=ImageDraw.Draw(image)
    for xy,text in [((5,5),'Front RGB'),((485,5),'Physical Lite3'),((5,275),'Overhead'),((485,275),'Depth: 0 to 5 m')]:
        draw.rectangle((xy[0]-2,xy[1]-2,xy[0]+180,xy[1]+15),fill='black');draw.text(xy,text,fill='white')
    draw.rectangle((0,518,960,540),fill='black');draw.text((5,523),label,fill='white')
    return np.asarray(image)

def episode(agent,mpc,case,root):
    out=root/case['id'];out.mkdir();frames=out/'frames';frames.mkdir();calls=out/'calls';calls.mkdir()
    random.seed(case['seed']);np.random.seed(case['seed']);torch.manual_seed(case['seed']);torch.cuda.manual_seed_all(case['seed'])
    agent.reset(1)
    backend=robot(case['scene']);cameras=Cameras(backend)
    for _ in range(600):backend.step((0.,0.))
    initial=backend.state();goal=np.array(initial.pose[:3])
    heading=np.array([np.cos(initial.pose[3]),np.sin(initial.pose[3])])
    left=np.array([-heading[1],heading[0]])
    goal[:2]+=case['distance_m']*heading
    (out/'case.json').write_text(json.dumps({**case,'initial_pose':initial.pose,'goal_world':goal.tolist(),
        'arrival_radius_m':.25,'active_wall_limit_s':40,'post_stop_s':2,'watchdog_s':.5,
        'goal_source':'Numerical point goal, not interpreted language','stop_owner':'external evaluator'},indent=2)+'\n')
    writer=Writer(frames);pool=ThreadPoolExecutor(max_workers=1);future=None
    seq=0;applied_seq=None;controls=None;received=None;control_sim_start=0.;records=[]
    began=time.monotonic();next_frame=began;termination=None;terminated=None
    watchdog_ticks=0;path_length=0.;last_xy=np.array(initial.pose[:2]);maximum_tilt=0.
    trajectory=[];error=None
    try:
        with (out/'trace.jsonl').open('w',buffering=1) as trace:
            while True:
                tick=time.monotonic();elapsed=tick-began
                if future is not None and future.done():
                    controls,record=future.result();future=None;records.append(record)
                    received=record['finished_mono'];control_sim_start=backend.data.time;applied_seq=record['seq']
                if termination is None and elapsed>=40:
                    termination='wall_timeout';terminated=tick
                if termination is None and future is None:
                    rgb,depth=cameras.observation()
                    pos=backend.data.qpos[backend.base_qpos:backend.base_qpos+3].copy()
                    quat=backend.data.qpos[backend.base_qpos+3:backend.base_qpos+7].copy()
                    capture=time.monotonic();seq+=1
                    obs=(rgb,depth,pos,quat,local_goal(goal,pos,quat),capture)
                    future=pool.submit(infer,agent,mpc,obs,calls,seq)
                watchdog=received is not None and tick-received>.5
                if termination is not None or controls is None or watchdog:
                    command=(0.,0.)
                else:
                    index=min(int((backend.data.time-control_sim_start)/.04),len(controls)-1)
                    command=tuple(map(float,controls[index]))
                if watchdog and termination is None:watchdog_ticks+=1
                for _ in range(4):backend.step(command)
                state=backend.state();distance=float(np.linalg.norm(np.array(state.pose[:2])-goal[:2]))
                maximum_tilt=max(maximum_tilt,state.telemetry['tilt_rad'])
                xy=np.array(state.pose[:2]);path_length+=float(np.linalg.norm(xy-last_xy));last_xy=xy
                if termination is None:
                    if state.telemetry['obstacle_contact_steps'] or state.telemetry['boundary_contact_steps']:
                        termination='contact_abort'
                    elif state.pose[2]<.18 or state.telemetry['tilt_rad']>.8:
                        termination='fall_abort'
                    elif distance<=.25:termination='external_goal_stop'
                    if termination:terminated=time.monotonic()
                now=time.monotonic()
                row={'mono':now,'wall_elapsed':now-began,'sim_time':float(backend.data.time),
                     'pose':state.pose,'velocity':state.velocity,'command':command,'applied_seq':applied_seq,
                     'goal_distance_m':distance,'watchdog':watchdog,'termination':termination,
                     'telemetry':state.telemetry}
                trace.write(json.dumps(row)+'\n');trajectory.append(row)
                if now>=next_frame:
                    rgb,depth=cameras.observation();chase,top=cameras.views()
                    label=f"{case['id']} | t={now-began:.1f}s | goal={distance:.2f}m | {termination or 'X-NavDP + original MPC'}"
                    writer.submit(montage(rgb,depth,chase,top,label),{'mono':now,'sim_time':float(backend.data.time)})
                    next_frame=now+.1
                if writer.error:raise RuntimeError(writer.error)
                if terminated is not None and now-terminated>=2:break
                time.sleep(max(0.,.02-(time.monotonic()-tick)))
    except BaseException as caught:
        error=repr(caught);termination='runtime_error'
        raise
    finally:
        if error:
            for _ in range(100):backend.step((0.,0.))
        pool.shutdown(wait=True,cancel_futures=True)
        writer.close();cameras.close()
        final=backend.state();final_distance=float(np.linalg.norm(np.array(final.pose[:2])-goal[:2]))
        result={'case':case,'termination':termination,'error':error,'final_pose':final.pose,
                'final_velocity':final.velocity,'final_goal_distance_m':final_distance,
                'forward_displacement_m':float((np.array(final.pose[:2])-np.array(initial.pose[:2]))@heading),
                'lateral_displacement_m':float((np.array(final.pose[:2])-np.array(initial.pose[:2]))@left),
                'path_length_m':path_length,'max_tilt_rad':maximum_tilt,
                'wall_seconds':time.monotonic()-began,'sim_seconds':float(backend.data.time)-3.,
                'model_calls_submitted':seq,'model_calls_consumed':len(records),'watchdog_ticks':watchdog_ticks,
                'frames':writer.count,'telemetry':final.telemetry,'stop_owner':'external evaluator',
                'success':termination=='external_goal_stop' and final_distance<=.25 and abs(final.velocity[0])<.1
                          and not final.telemetry['obstacle_contact_steps'] and not final.telemetry['boundary_contact_steps']}
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True);return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);args=parser.parse_args()
    root=EXP/'runs'/args.run;root.mkdir(parents=True,exist_ok=False)
    (root/'cases.json').write_text(json.dumps(CASES,indent=2)+'\n')
    stop_sampling=threading.Event()
    def sample_gpu():
        with (root/'gpu_samples.jsonl').open('w',buffering=1) as stream:
            while not stop_sampling.is_set():
                try:
                    usage=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.free,utilization.gpu',
                        '--format=csv,noheader,nounits'],text=True,timeout=5).strip()
                    record={'mono':time.monotonic(),'gpu':usage}
                except Exception as error:record={'mono':time.monotonic(),'error':repr(error)}
                stream.write(json.dumps(record)+'\n');stop_sampling.wait(.5)
    sampler=threading.Thread(target=sample_gpu,daemon=True);sampler.start()
    try:
        agent,identity=load_policy();(root/'model_identity.json').write_text(json.dumps(identity,indent=2)+'\n')
        mpc=load_mpc();results=[]
        for case in CASES:results.append(episode(agent,mpc,case,root))
        (root/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
    finally:stop_sampling.set();sampler.join(timeout=6)

if __name__=='__main__':main()
