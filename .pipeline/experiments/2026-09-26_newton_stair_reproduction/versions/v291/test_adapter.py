"""Exercise the actual adapter with mocked sensor/array plumbing, no solver steps."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import numpy as np

Q=np.tile([0.,-.8,1.6],4)
class Buffer:
    def __init__(self,value):self.value=np.asarray(value)
    def numpy(self):return self.value

class AdapterTests(unittest.TestCase):
    def make(self):
        # Geometry IDs deliberately shuffled; joints retain the real FL/FR/HL/HR order.
        model=NS(shape_count=4,shape_body=Buffer([0,1,2,3]),shape_type=Buffer([1]*4),
                 shape_scale=Buffer([[.022]*3]*4),shape_flags=Buffer([2]*4),
                 body_label=['lite3/HL_SHANK','lite3/FL_SHANK','lite3/HR_SHANK','lite3/FR_SHANK'],
                 joint_limit_lower=Buffer([-9.]*18),joint_limit_upper=Buffer([9.]*18))
        robot=NS(model=model,solver=NS(use_mujoco_cpu=True,mjc_geom_to_newton_shape=Buffer([[3,2,1,0]])),
                 q_indices=np.arange(7,19),qd_indices=np.arange(6,18),
                 state=NS(joint_q=Buffer([0,0,.5,0,0,0,1]+list(Q)),joint_qd=Buffer(np.zeros(18))),
                 policy_target=Q+.2,physics_time=lambda:20.,last_action=np.zeros(12))
        module_path=Path(__file__).with_name('newton_stance.py');spec=importlib.util.spec_from_file_location('adapter_test_subject',module_path)
        module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,newton=NS(GeoType=NS(SPHERE=1),ShapeFlags=NS(COLLIDE_SHAPES=2)),mujoco=NS()):
            spec.loader.exec_module(module);adapter=module.NewtonStance(robot)
        adapter.measure=lambda:np.array([30.,0.,0.,0.])
        return module,adapter,robot

    def test_geometry_mapping_and_applied_action(self):
        _,adapter,robot=self.make()
        self.assertEqual(adapter.geom_to_leg,{2:0,0:1,3:2,1:3})
        with patch.dict(sys.modules,lite3_newton=NS(Q0=Q,rotation_matrix=lambda q:np.eye(3))):
            adapter.update(np.zeros(3),Q+.09,20.,.5)
        np.testing.assert_allclose(robot.target[:3],Q[:3]+.09)
        np.testing.assert_allclose(robot.target[3:],Q[3:]+.2)
        np.testing.assert_allclose(robot.last_action,(robot.target-Q)/.25,rtol=1e-6)
        self.assertEqual(adapter.row['settling_contact_mask'],[True,False,False,False])
        self.assertFalse(adapter.row['policy_owns_joints'])

    def test_real_contact_measurement_maps_per_leg(self):
        module,adapter,robot=self.make()
        del adapter.measure
        robot.solver.mj_model=NS();robot.solver.mj_data=NS(ncon=2,contact=[NS(geom1=2,geom2=99),NS(geom1=99,geom2=0)])
        module.mujoco.mj_contactForce=lambda model,data,i,w:w.__setitem__(slice(None),[12.+i,0,0,0,0,0])
        np.testing.assert_array_equal(adapter.measure(),[12.,13.,0.,0.])

    def test_new_command_rejoin_keeps_actual_history(self):
        _,adapter,robot=self.make()
        with patch.dict(sys.modules,lite3_newton=NS(Q0=Q,rotation_matrix=lambda q:np.eye(3))):
            adapter.update(np.zeros(3),Q+.09,20.,.5);before=robot.target.copy();robot.physics_time=lambda:20.02
            robot.policy_target=Q+.3
            adapter.update(np.array([.3,0,0]),before,robot.motor_kp,robot.motor_kd)
        self.assertEqual(adapter.row['stance_mode'],'REJOIN')
        np.testing.assert_array_equal(robot.target,before)
        np.testing.assert_allclose(robot.last_action,(robot.target-Q)/.25,rtol=1e-6)

if __name__=='__main__':unittest.main()
