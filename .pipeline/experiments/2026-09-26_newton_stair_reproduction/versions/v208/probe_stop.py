"""Bounded original-geometry stop test initialized from an existing recording.

This restores measured robot state and policy history, not solver warm-start
buffers. Baseline/candidate receive identical initial data and zero commands.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys
import time

import numpy as np
from capture import RAW, SEEDS, seed_row

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
QUALIFIED=BASE.parent/'2026-09-26_newton_macos_policy'


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def restored_history(flat):
    pieces=np.split(np.asarray(flat,dtype=np.float32),np.cumsum(np.array([3,3,3,12,12,12])*10)[:-1])
    return np.concatenate([p.reshape(10,-1) for p in pieces],axis=1)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--variant',choices=['old','candidate'],required=True)
    parser.add_argument('--seed',choices=list(SEEDS),required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--preflight',action='store_true')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    row,source=seed_row(args.seed)
    if not args.preflight:
        manifest=json.loads((HERE/'manifest.json').read_text())
        for rel,expected in manifest['source_files'].items():
            assert hashlib.sha256((HERE/rel).read_bytes()).hexdigest()==expected,rel
    import warp as wp
    wp.config.kernel_cache_dir=os.environ['WARP_CACHE_PATH'];wp.init();wp.set_device('cpu')
    sys.path.insert(0,str(BASE/'scripts'))
    from robot_scene import StairRobot
    if args.variant=='candidate':
        from activate import install
        install()
    robot=StairRobot(stance_hold=True,startup_mode='policy',automatic_contact_capacity=True)
    expected_hold=(hashlib.sha256((HERE/'stance_hold.py').read_bytes()).hexdigest()
                   if args.variant=='candidate' else '9a97879a5d5ed2f7c9c3e327c1193b1c42cf079eaaf073a855afad53a7dbc306')
    assert robot.stance.status()['source_sha256']==expected_hold
    inherited={}
    for name,path in [('robot_scene.py',BASE/'scripts/robot_scene.py'),
                      ('scene_assets.py',BASE/'scripts/scene_assets.py'),
                      ('lite3_newton.py',QUALIFIED/'scripts/lite3_newton.py')]:
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest==hashlib.sha256((RAW/('executed_'+name)).read_bytes()).hexdigest(),name
        inherited[name]=digest
    robot.model.joint_q.assign(np.asarray(row['joint_q'],dtype=np.float32))
    robot.model.joint_qd.assign(np.asarray(row['joint_qd'],dtype=np.float32))
    robot.solver.reset(robot.state)
    robot.solver.mjw_data.time.assign(np.array([row['physics_time_s']],dtype=np.float32))
    robot.steps=row['physics_steps']
    robot.policy_calls=row['policy_calls']
    robot.history.values=restored_history(row['policy_input'])
    robot.last_action=np.asarray(row['action'],dtype=np.float32)
    robot.policy_input=np.asarray(row['policy_input'],dtype=np.float32)[None,:]
    robot.observation=np.asarray(row['observation'],dtype=np.float32)
    robot.target=np.asarray(row['target'],dtype=np.float64)
    robot.policy_target=robot.target.copy()
    robot.motor_kp=np.asarray(row['motor_kp'],dtype=np.float64)
    robot.motor_kd=np.asarray(row['motor_kd'],dtype=np.float64)
    robot.target_velocity=np.asarray(row['target_velocity'],dtype=np.float64)
    robot.effective_command=np.asarray(row['effective_command'],dtype=np.float32)
    q=robot.state.joint_q.numpy();qd=robot.state.joint_qd.numpy()
    np.testing.assert_allclose(q,row['joint_q'],atol=1e-6,rtol=0)
    np.testing.assert_allclose(qd,row['joint_qd'],atol=1e-6,rtol=0)
    np.testing.assert_allclose(robot.native_array('qpos')[:3],row['joint_q'][:3],atol=1e-6,rtol=0)
    terms=np.split(robot.history.values,np.cumsum([3,3,3,12,12,12])[:-1],axis=1)
    np.testing.assert_array_equal(np.concatenate([v.reshape(-1) for v in terms]),robot.policy_input[0])
    # Stance gate history has no stored targets while RL owns the joints. Reset
    # it equally for both arms; the measured physical state is not moved.
    assert row['policy_owns_joints'];robot.stance.hold.reset()
    request=dict(version='v208' if args.variant=='candidate' else 'v206_hold_control',
                 variant=args.variant,seed=args.seed,source_capture=str(RAW),source_telemetry=source,
                 source_time_s=row['physics_time_s'],source_state_sequence=row['state_sequence'],
                 duration_s=10.,full_route=False,command=[0.,0.,0.],
                 restoration='q, qd, applied targets/gains, last action, ten policy frames; solver caches rebuilt',
                 stance_source=robot.stance.status()['source_sha256'],
                 inherited_sources=inherited,
                 physics='original Building triangle mesh + Warp CPU contacts',preflight=args.preflight)
    write(args.output/'request.json',request)
    write(args.output/'initial_state.json',row)
    write(args.output/'preflight.json',dict(passed=True,source_time_s=robot.physics_time(),
                                         state_restored=True,policy_history_restored=True,physics_steps=0))
    if args.preflight:
        print(json.dumps({'preflight':True,'variant':args.variant,'seed':args.seed}));return
    started=time.monotonic();origin=robot.physics_time();initial=q[:3].copy()
    hold_since=None;longest_hold=0.;max_tilt=0.;max_speed=0.;max_omega=0.;max_xy=0.
    max_torque_step=0.;limit_samples=0;previous_torque=np.asarray(row['torque']);last_action=robot.last_action.copy()
    history_error=0.;first_transfer=None;first_fixed=None;last=None;fallen=False;minimum_fixed_force=None
    with (args.output/'telemetry.jsonl').open('w') as stream:
        for _ in range(501):
            if robot.physics_time()-origin>=10.:break
            robot.step([0.,0.,0.]);last=robot.telemetry();body=robot.body_and_sensor()
            elapsed=robot.physics_time()-origin
            last.update(body_sensor=body,elapsed_s=elapsed)
            stream.write(json.dumps(last)+'\n')
            speed=float(np.linalg.norm(body['linear_world']));omega=float(np.linalg.norm(body['angular_world']))
            tilt=float(np.degrees(np.arccos(np.clip(last['base_up_z'],-1,1))))
            max_tilt=max(max_tilt,tilt);max_speed=max(max_speed,speed);max_omega=max(max_omega,omega)
            max_xy=max(max_xy,float(np.linalg.norm(np.asarray(last['joint_q'][:2])-initial[:2])))
            torque=np.asarray(last['torque']);max_torque_step=max(max_torque_step,float(np.max(np.abs(torque-previous_torque))))
            previous_torque=torque
            limit_samples+=int(np.any(np.abs(torque)>=.95*np.tile([24.,24.,36.],4)))
            history_error=max(history_error,float(np.max(np.abs(np.asarray(last['observation'][33:45])-last_action))))
            last_action=np.asarray(last['action'])
            if last['stance_mode']=='STAND_TRANSITION' and first_transfer is None:first_transfer=elapsed
            if last['stance_mode']=='FIXED_STAND':
                if first_fixed is None:first_fixed=elapsed
                force=min(last['foot_forces_n'])
                minimum_fixed_force=force if minimum_fixed_force is None else min(minimum_fixed_force,force)
            stable=(last['stance_mode']=='FIXED_STAND' and not last['policy_owns_joints'] and
                    speed<=.03 and omega<=.05 and min(last['foot_forces_n'])>1 and
                    np.all(np.asarray(last['motor_kp'])==60) and np.all(np.asarray(last['motor_kd'])==1))
            hold_since=(robot.physics_time() if hold_since is None else hold_since) if stable else None
            if hold_since is not None:longest_hold=max(longest_hold,robot.physics_time()-hold_since)
            if last['base_up_z']<.5:fallen=True;break
    passed=(longest_hold>=2 and not fallen and history_error<1e-6 and robot.max_applied_torque_error<1e-4)
    result=dict(passed=passed,variant=args.variant,seed=args.seed,
                first_transfer_s=first_transfer,first_fixed_stand_s=first_fixed,
                longest_measured_pd_hold_s=longest_hold,final_stance_mode=last['stance_mode'],
                final_stance_reason=last['stance_reason'],final_foot_forces_n=last['foot_forces_n'],
                minimum_force_while_fixed_n=minimum_fixed_force,
                max_tilt_deg=max_tilt,max_linear_speed_mps=max_speed,max_angular_speed_radps=max_omega,
                max_xy_drift_m=max_xy,final_xy_drift_m=float(np.linalg.norm(np.asarray(last['joint_q'][:2])-initial[:2])),
                max_20ms_torque_change_nm=max_torque_step,control_samples_near_static_torque_limit=limit_samples,
                applied_history_max_error=history_error,applied_torque_max_error=robot.max_applied_torque_error,
                fallen=fallen,simulated_s=robot.physics_time()-origin,
                actual_physics_steps=robot.steps-row['physics_steps'],wall_s=time.monotonic()-started,
                stance=robot.stance.status(),navigation_acceptance=False)
    write(args.output/'result.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='stance'}),flush=True)


if __name__=='__main__':main()
