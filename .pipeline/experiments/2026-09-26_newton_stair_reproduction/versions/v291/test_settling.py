"""Behavioral tests on actual candidate StanceHold, without physics."""
import unittest
import numpy as np
import stance_hold as sh

Q = np.tile([0., -.8, 1.6], 4)


class Loop:
    def __init__(self, enabled=True, **kwargs):
        self.hold=sh.StanceHold('auto',entry_kd='xfade2s',settling_capture=enabled,**kwargs)
        self.target=Q+.09;self.kp=np.full(12,20.);self.kd=np.full(12,.5)

    def step(self,t,**kw):
        values=dict(now_s=t,command=np.zeros(3),joint_pos=Q.copy(),joint_vel=np.zeros(12),
                    policy_target=Q+.09,applied_target=self.target,applied_kp=self.kp,applied_kd=self.kd,
                    linear_speed=.01,angular_speed=.02,tilt_deg=3.,foot_forces=[55.,38.,0.,0.])
        values.update(kw);x=sh.HoldInput(**values);out=self.hold.update(x)
        self.target,self.kp,self.kd=out.target.copy(),out.kp.copy(),out.kd.copy()
        return x,out


class SettlingTests(unittest.TestCase):
    def test_only_loaded_quiet_legs_are_captured(self):
        loop=Loop();_,out=loop.step(20)
        np.testing.assert_array_equal(loop.hold.settling_contact_mask,[1,1,0,0])
        self.assertEqual(out.mode,'STAND_SETTLING');self.assertFalse(out.policy_owns_joints)
        _,out=loop.step(20.02,policy_target=Q+.19)
        np.testing.assert_allclose(out.target[:6],Q[:6]+.09)
        np.testing.assert_allclose(out.target[6:],Q[6:]+.19)
        np.testing.assert_array_equal(out.kp,np.full(12,20.))
        np.testing.assert_array_equal(out.kd,np.full(12,.5))

    def test_capture_matches_full_applied_torque(self):
        loop=Loop();qd=np.full(12,.3);kp=np.full(12,28.);kd=np.full(12,.7)
        x,out=loop.step(20,joint_vel=qd,applied_kp=kp,applied_kd=kd)
        before=kp*(x.applied_target-Q)-kd*qd
        after=out.kp*(out.target-Q)-out.kd*qd
        np.testing.assert_allclose(after[:6],before[:6],atol=1e-12)

    def test_lost_contact_releases_only_that_leg(self):
        loop=Loop();loop.step(20)
        _,out=loop.step(20.02,foot_forces=[0.,38.,0.,0.],policy_target=Q+.2)
        np.testing.assert_array_equal(loop.hold.settling_contact_mask,[0,1,0,0])
        np.testing.assert_allclose(out.target[:3],Q[:3]+.2)
        np.testing.assert_allclose(out.target[3:6],Q[3:6]+.09)

    def test_capture_does_not_bypass_four_foot_dwell(self):
        loop=Loop()
        for k in range(700):
            _,out=loop.step(20+k*.02)
            self.assertEqual(out.mode,'STAND_SETTLING')
        self.assertEqual(loop.hold.counters['entries'],0)

    def test_new_command_reuses_smooth_rejoin(self):
        loop=Loop();loop.step(20);previous=loop.target.copy()
        _,out=loop.step(20.02,command=[.3,0,0],policy_target=Q+.2)
        self.assertEqual(out.mode,'REJOIN');np.testing.assert_allclose(out.target,previous)
        self.assertFalse(loop.hold.settling_contact_mask.any())
        _,out=loop.step(20.28,command=[.3,0,0],policy_target=Q+.2)
        self.assertEqual(out.mode,'RL');np.testing.assert_allclose(out.target,Q+.2)

    def test_motion_and_tilt_release_assistance(self):
        for kw in (dict(linear_speed=.151),dict(angular_speed=.501),dict(tilt_deg=9.)):
            loop=Loop();loop.step(20)
            _,out=loop.step(20.02,policy_target=Q+.2,**kw)
            self.assertTrue(out.policy_owns_joints)
            np.testing.assert_allclose(out.target,Q+.2)
            self.assertFalse(loop.hold.settling_contact_mask.any())

    def test_fast_joint_or_airborne_foot_never_gets_captured(self):
        loop=Loop();qd=np.zeros(12);qd[0]=1.01
        loop.step(20,joint_vel=qd)
        np.testing.assert_array_equal(loop.hold.settling_contact_mask,[0,1,0,0])

    def test_no_policy_step_reintroduced_at_pd_entry(self):
        loop=Loop();loop.step(20,foot_forces=[55,38,17,20]);seed=loop.target.copy()
        for k in range(1,14):
            _,out=loop.step(20+k*.02,policy_target=Q+.18,foot_forces=[55,38,17,20])
        self.assertEqual(out.mode,'STAND_TRANSITION')
        np.testing.assert_allclose(out.target,seed)
        self.assertFalse(out.policy_owns_joints)
        _,out=loop.step(20.28,foot_forces=[55,38,17,0])
        self.assertEqual(out.mode,'RL');self.assertTrue(out.policy_owns_joints)

    def test_disabled_candidate_is_exact_parent(self):
        loop=Loop(False);base=sh.parent.StanceHold('auto',entry_kd='xfade2s')
        for k in range(150):
            x,out=loop.step(20+k*.02,foot_forces=[55,38,17,20])
            expected=base.update(x)
            self.assertEqual(out.mode,expected.mode)
            for name in ('target','kp','kd'):np.testing.assert_array_equal(getattr(out,name),getattr(expected,name))

    def test_nonfinite_policy_is_not_hidden_by_capture(self):
        loop=Loop();loop.step(20);policy=Q.copy();policy[0]=np.nan
        with self.assertRaises(sh.StanceHoldError):loop.step(20.02,policy_target=policy)

    def test_out_of_limit_capture_is_not_clipped_into_new_torque(self):
        loop=Loop(joint_lower=Q-.2,joint_upper=Q+.2)
        loop.step(20,applied_target=Q+1.)
        self.assertFalse(loop.hold.settling_contact_mask.any())

    def test_reset_clears_contact_targets(self):
        loop=Loop();loop.step(20);loop.hold.reset()
        self.assertFalse(loop.hold.settling_contact_mask.any())


if __name__=='__main__':unittest.main()
