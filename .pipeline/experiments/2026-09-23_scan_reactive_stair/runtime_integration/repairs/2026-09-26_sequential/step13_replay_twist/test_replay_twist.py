"""Exercise the actual replay twist writer at its message boundary."""
import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
import numpy as np

SOURCE = Path(__file__).resolve().parents[3] / "replay_stair_inputs.py"
spec = importlib.util.spec_from_file_location("stair_twist_replay", SOURCE)
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


class TwistTests(unittest.TestCase):
    def message(self, item):
        msg = NS(twist=NS(twist=NS(linear=NS(), angular=NS())))
        replay.assign_recorded_twist(msg,item)
        return [msg.twist.twist.linear.x,msg.twist.twist.linear.y,msg.twist.twist.linear.z], [
            msg.twist.twist.angular.x,msg.twist.twist.angular.y,msg.twist.twist.angular.z]

    def test_identity(self):
        linear,angular=self.message({"quaternion":[1,0,0,0],"linear":[1,2,3],"angular":[-2,0,1]})
        np.testing.assert_allclose(linear,[1,2,3],atol=1e-12)
        np.testing.assert_allclose(angular,[-2,0,1],atol=1e-12)

    def test_yaw_quarter_turn(self):
        s=math.sqrt(.5)
        linear,angular=self.message({"quaternion":[s,0,0,s],"linear":[1,0,0],"angular":[0,1,2]})
        np.testing.assert_allclose(linear,[0,-1,0],atol=1e-12)
        np.testing.assert_allclose(angular,[1,0,2],atol=1e-12)

    def test_roll_quarter_turn(self):
        s=math.sqrt(.5)
        linear,angular=self.message({"quaternion":[s,s,0,0],"linear":[0,1,0],"angular":[0,0,1]})
        np.testing.assert_allclose(linear,[0,0,-1],atol=1e-12)
        np.testing.assert_allclose(angular,[0,1,0],atol=1e-12)

    def test_invalid_rejected(self):
        for q in ([0,0,0,0],[2,0,0,0],[1,0,0],[float('nan'),0,0,0]):
            with self.assertRaises(ValueError):
                self.message({"quaternion":q,"linear":[1,0,0],"angular":[0,0,0]})
        with self.assertRaises(ValueError):
            self.message({"quaternion":[1,0,0,0],"linear":[float('inf'),0,0],"angular":[0,0,0]})

    def test_direct_body_fields(self):
        linear,angular=self.message({"linear_body":[1,2,3],"angular_body":[4,5,6]})
        self.assertEqual(linear,[1,2,3])
        self.assertEqual(angular,[4,5,6])
        with self.assertRaises(ValueError):
            self.message({"linear_body":[1,2,3]})


if __name__ == "__main__":
    unittest.main()
