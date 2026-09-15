"""Exercise metric depth, coordinates, physical walking, original model and MPC."""
import argparse
import json
import time
import numpy as np
import mujoco
from runtime import EXP, Cameras, infer, load_mpc, load_policy, local_goal, robot

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True)
    args=parser.parse_args();out=EXP/'runs'/args.run;out.mkdir(parents=True,exist_ok=False)
    checks={}
    q=np.array([np.sqrt(.5),0,0,np.sqrt(.5)])
    checks['body_goal_rotation']=bool(np.allclose(local_goal([0,1,0],[0,0,0],q),[1,0,0],atol=1e-6))
    b=robot('clear');c=Cameras(b)
    try:
        for _ in range(600):b.step((0.,0.))
        s=b.state();checks['stable_standing']=s.pose[2]>.25 and s.telemetry['tilt_rad']<.3
        start=np.array(s.pose)
        for _ in range(400):b.step((.3,0.))
        end=b.state();checks['physical_forward_motion']=bool(end.pose[0]-start[0]>.25 and end.pose[2]>.25)
        checks['floor_is_not_obstacle']=end.telemetry['obstacle_contact_steps']==0 and end.telemetry['boundary_contact_steps']==0
        obstacle_robot=robot('blocked')
        obstacle_robot.data.qpos[obstacle_robot.base_qpos:obstacle_robot.base_qpos+3]=[8.0,13.8,.35]
        mujoco.mj_forward(obstacle_robot.model,obstacle_robot.data)
        obstacle_robot.step((0.,0.))
        checks['physical_obstacle_contact_detected']=obstacle_robot.obstacle_contact_steps>0
        rgb,depth=c.observation();np.savez_compressed(out/'camera.npz',rgb=rgb,depth=depth)
        from PIL import Image
        Image.fromarray(rgb).save(out/'front.png')
        checks['rgb_depth_shapes']=rgb.shape==(270,480,3) and depth.shape==(270,480)
        wall=mujoco.MjModel.from_xml_string('<mujoco><worldbody><camera name="test" pos="0 0 0" quat="-0.5 -0.5 0.5 0.5"/><geom type="box" pos="2.1 0 0" size="0.1 10 10"/></worldbody></mujoco>')
        d=mujoco.MjData(wall);mujoco.mj_forward(wall,d)
        renderer=mujoco.Renderer(wall,height=270,width=480);renderer.update_scene(d,camera='test');renderer.enable_depth_rendering()
        measured=float(renderer.render()[135,240]);renderer.close()
        checks['metric_depth_2m_wall']=abs(measured-2.0)<.005
        mpc=load_mpc()
        for name,sign in [('forward',1),('reverse',-1)]:
            path=np.zeros((1,25,3));path[0,:,0]=np.linspace(0,sign,25)
            commands,_,_,_=mpc.solve(path)
            checks['mpc_'+name]=bool(sign*np.mean(commands[0,:10,0])>.05 and np.max(np.abs(commands))<=.5001)
        agent,identity=load_policy();agent.reset(1)
        pos=b.data.qpos[b.base_qpos:b.base_qpos+3].copy()
        quat=b.data.qpos[b.base_qpos+3:b.base_qpos+7].copy()
        _,record=infer(agent,mpc,(rgb,depth,pos,quat,np.array([2.,0,0],np.float32),time.monotonic()),out,1)
        checks['original_cuda_inference']=True
        result={'checks':checks,'identity':identity,'depth_wall_m':measured,
                'standing_pose':s.pose,'walking_pose':end.pose,'inference_seconds':record['model_seconds']}
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
        if not all(checks.values()):raise RuntimeError('Preflight assertion failed')
    finally:c.close()

if __name__=='__main__':main()
