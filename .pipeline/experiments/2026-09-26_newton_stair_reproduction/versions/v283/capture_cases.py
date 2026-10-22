"""New-pose original geometric LiDAR, paired captured states; zero physics."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib,importlib.util,json,os,sys
import numpy as np

HERE=Path(__file__).resolve().parent;VERSIONS=HERE.parent;EXP=HERE.parents[1]
OUT=Path('/home/sun/vla_exec/navigation_geometry_v283/cohort')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def pose_file(path,xyz,wxyz):
    path.write_text(' '.join(map(str,list(xyz)+list(wxyz[1:])+[wxyz[0]]))+'\n')

def main():
    import warp as wp
    wp.config.kernel_cache_dir=str(OUT/'warp-cache');wp.init();wp.set_device('cpu')
    spec=importlib.util.spec_from_file_location('case_locomotion',VERSIONS/'v216/activate.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.install()
    sys.path[:0]=[str(VERSIONS/'v40/physics'),str(EXP/'scripts'),str(VERSIONS/'v237')]
    from robot_scene_v40 import StairRobot
    from geometric_lidar import GeometricLidar
    from scan_deadline import ScanDeadline
    from lite3_newton_v40 import check_golden_policy
    (OUT/'policy_golden.json').write_text(json.dumps(check_golden_policy(),indent=2)+'\n')
    manifest=json.loads((OUT/'cases_manifest.json').read_text())
    for case in manifest['cases']:
        folder=OUT/'cases'/case['case_id'];p=folder/'scenario.json'
        assert sha(p)==case['scenario_sha256']
        if (folder/'fixture.json').exists():
            previous=json.loads((folder/'fixture.json').read_text())
            for name,h in previous['files'].items():assert sha(folder/name)==h
            assert previous['physics_steps']==0 and previous['scenario_sha256']==case['scenario_sha256']
            continue
        scenario=json.loads(p.read_text());scenario['spawn_body_height_m']=.3
        robot=StairRobot(startup_mode='policy',stance_hold=True,scenario=scenario,
            model_device='cpu',use_solver_graph=True,automatic_contact_capacity=True)
        lidar=GeometricLidar(robot,None,emitter_self_exclusion=True,visible_human_only=True)
        pose=robot.body_and_sensor();before=robot.state.body_q.numpy().copy()
        expected=np.array(case['start']['ground']);expected[2]+=.3
        assert np.linalg.norm(np.array(pose['position'])-expected)<1e-5
        # Compile the original ray kernels before measuring the captured budget.
        warm=robot.model.state();warm.body_q.assign(robot.state.body_q)
        lidar.scan(0,0.,override_pose=pose,captured_state=warm)
        deadline=ScanDeadline();records=[];listing=[]
        with ThreadPoolExecutor(max_workers=1) as pool:
            for index in range(6):
                captured=robot.model.state();captured.body_q.assign(robot.state.body_q)
                future=deadline.submit(pool,lidar.scan,index,index*.1,override_pose=pose,captured_state=captured)
                local,world,info,_,_=deadline.result(future)
                stem=f'scan_{index:02d}';body=stem+'_body.txt';sensor=stem+'_sensor.txt';cloud=stem+'.f32'
                pose_file(folder/body,pose['position'],pose['quaternion'])
                pose_file(folder/sensor,pose['sensor_position'],pose['sensor_quaternion'])
                local.astype('<f4').tofile(folder/cloud);world.astype('<f4').tofile(folder/(stem+'_world.f32'))
                stamp=1000000000+index*100000000
                listing.append(f'{index} {stamp} {body} {sensor} {cloud}\n')
                records.append(dict(index=index,stamp_ns=stamp,info=info,
                    local_sha256=sha(folder/cloud),world_sha256=sha(folder/(stem+'_world.f32'))))
        assert robot.steps==0 and np.array_equal(before,robot.state.body_q.numpy())
        (folder/'scans.txt').write_text(''.join(listing))
        deadline.save(folder/'scan_timing.jsonl')
        record=dict(case_id=case['case_id'],physics_steps=0,captured_state_unchanged=True,
            fixture_kind='stationary nominal standing pose; not a physical startup',
            period_s=.1,absolute_wall_budget_s=.1,body_sensor=pose,records=records,
            scenario_sha256=case['scenario_sha256'],max_scan_s=max(r['total_s'] for r in deadline.records),
            files={p.name:sha(p) for p in folder.iterdir() if p.is_file()})
        (folder/'fixture.json').write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps({k:v for k,v in record.items() if k in ('case_id','physics_steps','max_scan_s')}),flush=True)

if __name__=='__main__':main()
