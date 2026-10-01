"""Bounded observation of the frozen Building physics path; no timestamps changed."""
from pathlib import Path
import hashlib
import inspect
import json
import os
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
assert str(ROOT) == "/home/sun/vla_exec/vla", "Run only on the authorized execution copy"
os.environ["WARP_CACHE_PATH"] = str(HERE / "worker_cache")
import numpy as np
import warp as wp
wp.config.kernel_cache_dir = str(HERE / "worker_cache")
wp.init()
wp.set_device("cpu")
sys.path[:0] = [str(BASE / "scripts"), str(BASE / "runtime_sources/bridge")]
from robot_scene import StairRobot


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = HERE / "cpu_profile01"
    out.mkdir()
    shutil_source = out / "executed_profile_cpu.py"
    shutil_source.write_bytes(Path(__file__).read_bytes())
    frozen=json.loads((BASE/"versions/v35/manifest.json").read_text())
    for name,digest in frozen["source_files"].items():
        assert sha(ROOT/name)==digest,name
    started=time.monotonic()
    scenario=json.loads((BASE/"inputs/historical_full_building.json").read_text())
    robot=StairRobot(startup_mode="policy",stance_hold=False,automatic_contact_capacity=True,scenario=scenario)
    modules={str(Path(inspect.getfile(cls))):sha(Path(inspect.getfile(cls))) for cls in
             (StairRobot, robot.__class__.__bases__[0], robot.solver.__class__)}
    samples={"policy_infer":[],"collision_pipeline":[],"solver_step":[],"motor_substep":[],"body_pose":[],"control_step":[]}
    def observe(obj,name,group):
        original=getattr(obj,name)
        def timed(*args,**kwargs):
            before=time.perf_counter()
            try:return original(*args,**kwargs)
            finally:samples[group].append(time.perf_counter()-before)
        setattr(obj,name,timed)
    observe(robot,"infer","policy_infer")
    observe(robot,"_motor_substep","motor_substep")
    observe(robot.solver,"step","solver_step")
    observe(robot.collision_pipeline,"collide","collision_pipeline")
    poses=[]
    def body_observer(current):
        if current.steps%5==0:
            before=time.perf_counter()
            pose=current.body_and_sensor()
            samples["body_pose"].append(time.perf_counter()-before)
            poses.append({"step":current.steps,"position":pose["position"],"quaternion":pose["quaternion"]})
    robot.physics_observer=body_observer
    command=np.zeros(3,np.float32)
    for _ in range(5):robot.step(command)
    for values in samples.values():values.clear()
    poses.clear()
    wp.synchronize()
    physics_start=robot.physics_time()
    policy_start=robot.policy_calls
    motor_start=robot.steps
    wall_start=time.perf_counter()
    for _ in range(100):
        before=time.perf_counter()
        robot.step(command)
        samples["control_step"].append(time.perf_counter()-before)
    wp.synchronize()
    wall_elapsed=time.perf_counter()-wall_start
    physics_elapsed=robot.physics_time()-physics_start
    stats={key:{"count":len(values),"total_wall_s":sum(values),"median_s":float(np.median(values)),
        "p95_s":float(np.percentile(values,95)),"max_s":max(values)} for key,values in samples.items() if values}
    evidence={"device":str(robot.model.device),"newton_contacts":robot.collision_pipeline is not None,
        "use_mujoco_cpu":robot.solver.use_mujoco_cpu,"startup_mode":"policy","zero_command":True,
        "warmup_policy_steps":5,"measured_policy_steps":robot.policy_calls-policy_start,"measured_physics_steps":robot.steps-motor_start,
        "actual_solver_elapsed_s":physics_elapsed,"wall_elapsed_s":wall_elapsed,"rtf":physics_elapsed/wall_elapsed,
        "measured_policy_wall_hz":(robot.policy_calls-policy_start)/wall_elapsed,
        "measured_physics_wall_hz":(robot.steps-motor_start)/wall_elapsed,"target_rtf":1.,"statistics":stats,
        "module_sha256":modules,"initialization_and_audit_wall_s":time.monotonic()-started,
        "max_applied_torque_error":robot.max_applied_torque_error,"navigation_run":False,
        "sensing_transport_included":False,"claim":"Physics-only ceiling with measured-pose reads; full stack remains unmeasured."}
    (out/"samples.json").write_text(json.dumps(samples)+"\n")
    (out/"poses.json").write_text(json.dumps(poses)+"\n")
    (out/"result.json").write_text(json.dumps(evidence,indent=2)+"\n")
    records={str(p.relative_to(ROOT)):{"sha256":sha(p),"bytes":p.stat().st_size} for p in out.iterdir() if p.is_file()}
    (out/"return_manifest.json").write_text(json.dumps(records,indent=2)+"\n")
    print(json.dumps(evidence,indent=2),flush=True)


if __name__ == "__main__":
    main()
