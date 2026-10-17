"""Behavior checks at the real hold input/output seam, without a simulator."""
import unittest
import numpy as np
import stance_hold as sh

Q = np.tile([0., -.8, 1.6], 4)


class Loop:
    def __init__(self):
        self.hold = sh.StanceHold('auto', entry_kd='xfade2s')
        self.target, self.kp, self.kd = Q+.09, np.full(12,20.), np.full(12,.5)

    def step(self, t, **kwargs):
        values = dict(now_s=t, command=np.zeros(3), joint_pos=Q.copy(), joint_vel=np.zeros(12),
                      policy_target=Q+.09, applied_target=self.target, applied_kp=self.kp,
                      applied_kd=self.kd, linear_speed=.01, angular_speed=.02, tilt_deg=3.,
                      foot_forces=np.array([55.,38.,17.,20.]))
        values.update(kwargs)
        x = sh.HoldInput(**values)
        out = self.hold.update(x)
        self.target,self.kp,self.kd = out.target,out.kp,out.kd
        return x,out

    def enter(self, **kwargs):
        for k in range(14):
            x,out = self.step(20+k*.02, **kwargs)
        assert out.mode == 'STAND_TRANSITION'
        return x,out


class ReturnTests(unittest.TestCase):
    def test_uneven_and_missing_foot_loads_do_not_block_stillness(self):
        for forces in ([55,38,17,20],[40,0,0,40],[0,0,0,0]):
            with self.subTest(forces=forces):
                loop=Loop()
                for k in range(14):
                    _,out=loop.step(20+k*.02,foot_forces=forces)
                    self.assertEqual(out.mode,'STAND_SETTLING' if k<13 else 'STAND_TRANSITION')
                self.assertEqual(out.reason,'still_confirmed')
                self.assertFalse(out.policy_owns_joints)

    def test_each_motion_gate_blocks_without_forced_timeout(self):
        cases=[dict(linear_speed=.16),dict(angular_speed=.51),dict(tilt_deg=8.60),
               dict(joint_vel=np.r_[1.01,np.zeros(11)]),dict(joint_vel=np.r_[-1.01,np.zeros(11)])]
        for case in cases:
            with self.subTest(case=case):
                loop=Loop()
                for k in range(650):
                    _,out=loop.step(20+k*.02,**case)
                    self.assertEqual(out.mode,'STAND_SETTLING')
                    self.assertTrue(out.policy_owns_joints)
                self.assertEqual(loop.hold.counters['entries'],0)

    def test_one_moving_frame_restarts_complete_dwell(self):
        loop=Loop()
        for k in range(12):loop.step(20+k*.02)
        loop.step(20.24,joint_vel=np.full(12,1.1))
        for k in range(14):
            _,out=loop.step(20.26+k*.02)
            self.assertEqual(out.mode,'STAND_SETTLING' if k<13 else 'STAND_TRANSITION')

    def test_two_second_transfer_stiffness_law_and_measured_target_cap(self):
        loop=Loop();x,out=loop.enter(policy_target=Q+.9)
        np.testing.assert_array_equal(out.target,x.policy_target)
        np.testing.assert_array_equal(out.kp,np.full(12,20.))
        seed=loop.hold._hold_target.copy()
        measured=Q-.1
        x,out=loop.step(21.26,joint_pos=measured,policy_target=Q+.4)
        expected_hold=measured+np.clip(seed-measured,-.2,.2)
        np.testing.assert_allclose(out.kp,np.full(12,40.))
        np.testing.assert_allclose(out.kp*(out.target-measured),
            .5*20*(x.policy_target-measured)+.5*60*(expected_hold-measured))
        _,out=loop.step(22.26,joint_pos=measured)
        self.assertEqual(out.mode,'FIXED_STAND')
        np.testing.assert_allclose(out.target,expected_hold)
        measured=Q-.3
        _,out=loop.step(22.28,joint_pos=measured)
        self.assertLessEqual(np.max(np.abs(out.target-measured)),.2000000001)

    def test_capture_is_torque_matched_and_has_no_nominal_pose_reset(self):
        loop=Loop();q=Q+np.linspace(-.3,.3,12)
        x,_=loop.enter(joint_pos=q)
        np.testing.assert_allclose(loop.hold._hold_target,q+x.applied_kp/60*(x.applied_target-q))
        self.assertFalse(np.allclose(loop.hold._hold_target,Q))

    def test_new_command_cancels_wait_and_rejoins_transition(self):
        loop=Loop();loop.step(20.)
        _,out=loop.step(20.02,command=[.1,0,0]);self.assertEqual(out.mode,'RL')
        loop=Loop();loop.enter()
        _,out=loop.step(20.28,command=[.1,0,0]);self.assertEqual(out.mode,'REJOIN')
        _,out=loop.step(20.54,command=[.1,0,0]);self.assertEqual(out.mode,'RL')

    def test_factory_fixed_hold_is_not_target_capped(self):
        loop=Loop();hold=loop.hold
        hold._hold_target=Q+.3;hold._set_mode('FIXED_STAND','measured_factory_stand',20.)
        _,out=loop.step(20.,foot_forces=[30]*4)
        np.testing.assert_allclose(out.target,Q+.3)
        self.assertEqual(out.mode,'FIXED_STAND')

    def test_original_disturbance_exit_remains(self):
        loop=Loop();loop.enter();loop.step(22.26)
        for k in range(14):_,out=loop.step(22.28+k*.02,linear_speed=.2)
        self.assertEqual(out.mode,'RL')
        self.assertEqual(out.reason,'fixed_stand_disturbance:linear_speed')

    def test_off_mode_remains_policy_pass_through(self):
        loop=Loop();loop.hold=sh.StanceHold('off')
        x,out=loop.step(0.,policy_target=Q+.25)
        np.testing.assert_array_equal(out.target,x.policy_target)
        self.assertTrue(out.policy_owns_joints)

    def test_nonfinite_joint_speed_fails(self):
        with self.assertRaises(sh.StanceHoldError):Loop().step(20.,joint_vel=np.full(12,np.nan))


if __name__=='__main__':unittest.main()
