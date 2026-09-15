"""Thin integration around the original X-NavDP model and acados controller."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import time

import mujoco
import numpy as np

EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP))
sys.path.insert(0, str(EXP/'work/x-navdp/eval/src'))
from lib.robots.lite3 import Lite3Backend, rotation_matrix

def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def local_goal(goal_world, base_pos, quat_wxyz):
    delta = np.asarray(goal_world) - np.asarray(base_pos)
    goal = rotation_matrix(quat_wxyz).T @ delta
    goal[2] = 0.0  # Original HTTP interface transports x/y and fixes z=0.
    return goal.astype(np.float32)

def robot(scene):
    return Lite3Backend(EXP/'assets/lite3/lite3.xml', EXP/'policy/policy_stateless_h10.onnx',
                        scene_source=EXP/'cases'/f'{scene}.xml')

def load_policy():
    import torch
    from policy_agent import NavDP_Agent
    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    manifest = json.loads((EXP/'setup/selected_model.json').read_text())
    checkpoint = EXP/'models'/manifest['file']
    if file_hash(checkpoint) != manifest['sha256']:
        raise RuntimeError('Checkpoint SHA-256 mismatch')
    focal = 270 / (2*np.tan(np.deg2rad(79.865)/2))
    intrinsic = np.array([[focal,0,240],[0,focal,135],[0,0,1]],dtype=np.float32)
    agent = NavDP_Agent(intrinsic, navi_model=str(checkpoint), embodiment=2,
                        is_real=False, device='cuda:0')
    state = torch.load(checkpoint, map_location='cpu', weights_only=True)
    required=set(agent.navi_former.state_dict())
    unused=sorted(set(state)-required)
    allowed=('pixel_encoder.','image_encoder.','critic_head.')
    if required-set(state) or any(k!='log_alpha' and not k.startswith(allowed) for k in unused):
        raise RuntimeError('Unexplained checkpoint/runtime key mismatch')
    checked = agent.navi_former.load_state_dict({k:state[k] for k in required}, strict=True)
    identity = {'torch':torch.__version__, 'cuda':torch.version.cuda,
                'device':torch.cuda.get_device_name(0),
                'checkpoint_sha256':file_hash(checkpoint),
                'parameter_count':sum(p.numel() for p in agent.navi_former.parameters()),
                'parameter_dtypes':sorted({str(p.dtype) for p in agent.navi_former.parameters()}),
                'missing_keys':checked.missing_keys,'unexpected_keys':checked.unexpected_keys,
                'unused_training_key_count':len(unused),'unused_training_keys':unused}
    return agent, identity

def load_mpc():
    source = EXP/'work/x-navdp/src/utils/mpc_tracking.py'
    spec = importlib.util.spec_from_file_location('xnavdp_original_mpc', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BatchMPCController(batch=1,N=75,desired_v=0.5,v_max=0.5,
                                     w_max=0.5,ref_gap=3,T=0.04)

class Cameras:
    def __init__(self, backend):
        self.backend = backend
        self.renderer = mujoco.Renderer(backend.model,height=270,width=480)
        self.top = mujoco.MjvCamera()
        self.top.lookat[:] = [8.5,13.8,0.0]
        self.top.distance = 7
        self.top.azimuth = 90
        self.top.elevation = -89.9
        if hasattr(self.top,'orthographic'):
            self.top.orthographic = 1

    def observation(self):
        self.renderer.disable_depth_rendering()
        self.renderer.update_scene(self.backend.data,camera=self.backend.camera_name)
        rgb = self.renderer.render().copy()
        self.renderer.enable_depth_rendering()
        depth = self.renderer.render().copy()
        self.renderer.disable_depth_rendering()
        if not np.isfinite(depth).all() or np.any(depth <= 0):
            raise RuntimeError('Invalid rendered metric depth')
        return rgb,depth

    def views(self):
        result=[]
        for camera in ['lite3/robot_chase', self.top]:
            self.renderer.update_scene(self.backend.data,camera=camera)
            result.append(self.renderer.render().copy())
        return result

    def close(self):
        self.renderer.close()

def infer(agent, mpc, observation, destination, seq):
    """Keep original preprocessing, diffusion gradients, critic and recovery logic."""
    import torch
    rgb,depth,pos,quat,goal,capture = observation
    started=time.monotonic()
    np.savez_compressed(destination/f'input_{seq:04d}.npz',rgb=rgb,depth=depth,
                        pos=pos,quat_wxyz=quat,goal=goal,capture_mono=capture)
    inference_started=time.monotonic()
    path,candidates,values,_ = agent.step_pointgoal_with_guidance(
        goal[None,:],rgb[None,...],depth[None,...,None].copy(),
        pos[None,:],quat[[1,2,3,0]][None,:])
    torch.cuda.synchronize()
    predicted=time.monotonic()
    if path.shape != (1,24,3) or not np.isfinite(path).all() or not np.isfinite(values).all():
        raise RuntimeError(f'Invalid model result {path.shape}')
    reference=np.concatenate([np.zeros_like(path[:,:1]),path],axis=1)
    controls,states,_,_=mpc.solve(reference)
    solver_status=int(mpc.controller.solver.status)
    if controls.shape != (1,75,2) or not np.isfinite(controls).all():
        raise RuntimeError(f'Invalid MPC result {controls.shape}')
    finished=time.monotonic()
    record={'seq':seq,'capture_mono':capture,'started_mono':started,'finished_mono':finished,
            'input_write_seconds':inference_started-started,
            'model_seconds':predicted-inference_started,'mpc_seconds':finished-predicted,
            'path':path.tolist(),'all_paths':candidates.tolist(),'q_values':values.tolist(),
            'mpc_status':solver_status,
            'controls':controls.tolist(),'stuck':agent.is_stuck.tolist(),
            'input_sha256':file_hash(destination/f'input_{seq:04d}.npz')}
    (destination/f'output_{seq:04d}.json').write_text(json.dumps(record)+'\n')
    if solver_status!=0:raise RuntimeError(f'Original MPC failed with status {solver_status}')
    return controls[0],record
