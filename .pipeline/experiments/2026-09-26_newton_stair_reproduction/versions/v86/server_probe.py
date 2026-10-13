"""Exercise the real Foxy ControllerServer with explicit fake planner/stop evidence.

No simulator, hardware driver or actuator is started. This qualifies ROS action,
plugin and tagged-output integration; it does not qualify native planning safety.
"""
import json
import os
from pathlib import Path
import subprocess
import time

import rclpy
from ament_index_python.packages import get_package_prefix
from rclpy.action import ActionClient
from rclpy.node import Node
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, TransformStamped, Twist
from lifecycle_msgs.srv import ChangeState
from nav_msgs.msg import Odometry
from nav2_msgs.action import FollowPath
from tf2_msgs.msg import TFMessage
from scan_planner_msgs.msg import Bspline, P2BRoute, P2BCancel, P2BAdmission
from scan_planner_msgs.msg import P2BExecutionSafety, P2BStopEvidence, P2BStampedTwist


def identity(source, target):
    for key in ("run_id", "epoch", "request_id", "goal_id", "route_id", "command_id",
                "generation", "map_epoch", "map_revision"):
        setattr(target, key, getattr(source, key))


class Probe(Node):
    def __init__(self):
        super().__init__("scan_nav2_protocol_probe")
        self.x = 0.0
        self.active = None
        self.curve_sent = False
        self.raw = []
        self.plain = []
        self.cancels = []
        self.ready = []
        self.tf = self.create_publisher(TFMessage, "/tf", 10)
        self.odom = self.create_publisher(Odometry, "/odom", 10)
        self.binding = self.create_publisher(P2BRoute, "/nav2_scan/route_binding", 10)
        self.splines = self.create_publisher(Bspline, "/quad_0/planning/bspline", 10)
        self.safety = self.create_publisher(P2BExecutionSafety, "/quad_0/planning/execution_safety", 10)
        self.evidence = self.create_publisher(P2BStopEvidence, "/nav2_scan/stop_evidence", 10)
        self.create_subscription(P2BRoute, "/p2b/route", self.on_route, 10)
        self.create_subscription(P2BRoute, "/nav2_scan/binding_ready", self.ready.append, 10)
        self.create_subscription(P2BCancel, "/p2b/scan_cancel", self.cancels.append, 10)
        self.create_subscription(P2BStampedTwist, "/quad_0/raw_scan_cmd_vel", self.raw.append, 20)
        self.create_subscription(Twist, "/cmd_vel", self.plain.append, 10)
        self.timer = self.create_timer(0.02, self.publish_inputs)
        self.action = ActionClient(self, FollowPath, "/follow_path")

    def on_route(self, route):
        self.active = route
        self.curve_sent = False

    def pose(self, x):
        pose = PoseStamped()
        pose.header.frame_id = "world"
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.z = 0.42
        pose.pose.orientation.w = 1.0
        return pose

    def publish_inputs(self):
        stamp = self.get_clock().now().to_msg()
        tf = TransformStamped()
        tf.header.frame_id = "world"
        tf.header.stamp = stamp
        tf.child_frame_id = "base_link"
        tf.transform.translation.x = self.x
        tf.transform.translation.z = 0.42
        tf.transform.rotation.w = 1.0
        self.tf.publish(TFMessage(transforms=[tf]))
        odom = Odometry()
        odom.header = tf.header
        odom.child_frame_id = "base_link"
        odom.pose.pose = self.pose(self.x).pose
        self.odom.publish(odom)
        if self.active is None:
            return
        if not self.curve_sent:
            curve = Bspline()
            identity(self.active, curve)
            curve.order = 3
            curve.traj_id = self.active.generation
            curve.start_time = stamp
            curve.pos_pts = [self.pose(self.x + i * 0.4).pose.position for i in range(6)]
            curve.knots = [float(i) for i in range(-3, 7)]
            self.splines.publish(curve)
            self.curve_sent = True
        safety = P2BExecutionSafety()
        identity(self.active, safety.binding)
        safety.binding.consumer = "native_safety"
        safety.binding.traj_id = self.active.generation
        safety.stamp = stamp
        safety.observation_stamp_s = self.get_clock().now().nanoseconds / 1e9
        safety.clear = True
        safety.local_map_revision = 1
        self.safety.publish(safety)

    def wait(self, predicate, timeout=5.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.01)
            if predicate():
                return
        raise TimeoutError("Protocol probe condition timed out")

    def pause(self, duration):
        deadline = time.monotonic() + duration
        self.wait(lambda: time.monotonic() >= deadline, duration + 1.0)

    def transition(self, transition_id):
        client = self.create_client(ChangeState, "/controller_server/change_state")
        self.wait(lambda: client.service_is_ready(), 10.0)
        request = ChangeState.Request()
        request.transition.id = transition_id
        future = client.call_async(request)
        self.wait(future.done, 15.0)
        assert future.result().success, transition_id

    def route(self, generation):
        route = P2BRoute()
        route.run_id = "server_probe"
        route.epoch = 1
        route.request_id = f"request{generation}"
        route.goal_id = f"goal{generation}"
        route.route_id = f"route{generation}"
        route.command_id = f"command{generation}"
        route.generation = generation
        route.map_epoch = "map"
        route.map_revision = 1
        route.has_goal_pose = True
        route.goal_pose = self.pose(8.0).pose
        route.path.header = self.pose(self.x).header
        route.path.poses = [self.pose(self.x), self.pose(7.5)]
        return route

    def start(self, route):
        deadline = time.monotonic() + 1.5
        while not any(message == route for message in self.ready):
            if time.monotonic() >= deadline:
                raise TimeoutError("Route binding was not acknowledged while fresh")
            self.binding.publish(route)
            try:
                self.wait(lambda: any(message == route for message in self.ready), 0.15)
            except TimeoutError:
                continue
        self.wait(lambda: self.action.server_is_ready())
        future = self.action.send_goal_async(FollowPath.Goal(path=route.path, controller_id="SCAN"))
        self.wait(future.done)
        handle = future.result()
        assert handle.accepted
        return handle, handle.get_result_async()

    def stop_proof(self, route, measured):
        proof = P2BStopEvidence()
        identity(route, proof.admission)
        proof.admission.consumer = "controller"
        proof.admission.status = "stopped"
        proof.admission.hold_confirmed = True
        proof.admission.measured_stillness_confirmed = measured
        proof.stamp = self.get_clock().now().to_msg()
        self.evidence.publish(proof)
        self.pause(0.05)


def main():
    result_dir = Path(os.environ["V86_RESULT_DIR"])
    result_dir.mkdir(parents=True, exist_ok=False)
    source_params = Path(os.environ["V86_PARAMS"])
    text = source_params.read_text()
    marker = "      native_worker_enabled: true"
    if text.count(marker) != 1:
        raise ValueError("Expected one explicit native-worker setting in the component profile")
    params = result_dir / "fake_planner_profile.yaml"
    params.write_text(text.replace(marker, "      native_worker_enabled: false"))
    result = {"scope": "real Foxy ControllerServer, real SCAN plugins, fake planner/TF/physical-stop evidence",
              "robot_actuation": False, "physics": False, "passed": False}
    log = (result_dir / "server.log").open("w")
    executable = str(Path(get_package_prefix("nav2_controller")) / "lib/nav2_controller/controller_server")
    process = subprocess.Popen([executable,
                                "--ros-args", "--params-file", str(params)], stdout=log, stderr=subprocess.STDOUT)
    rclpy.init()
    node = Probe()
    try:
        node.transition(1)
        node.transition(3)
        route = node.route(1)
        handle, done = node.start(route)
        node.wait(lambda: any(m.generation == 1 and m.twist.linear.x > 0 for m in node.raw))
        cancellation = handle.cancel_goal_async()
        node.wait(cancellation.done)
        node.wait(done.done)
        assert done.result().status == GoalStatus.STATUS_CANCELED, done.result().status
        node.wait(lambda: len(node.cancels) > 0)
        node.pause(0.15)
        assert node.raw[-1].twist == Twist()
        count = len(node.raw)
        node.pause(0.15)
        assert all(m.twist == Twist() for m in node.raw[count:])
        node.stop_proof(route, True)
        node.x = 7.5
        route2 = node.route(2)
        _, done2 = node.start(route2)
        node.wait(lambda: any(m.generation == 2 for m in node.raw))
        node.pause(0.1)
        assert not done2.done(), "Grid-snapped endpoint was incorrectly accepted as requested goal"
        node.x = 8.0
        node.wait(lambda: any(m.generation == 2 for m in node.cancels))
        assert not done2.done(), "Goal succeeded before physical-stop evidence"
        node.stop_proof(route2, False)
        assert not done2.done(), "Controller hold was mistaken for measured stillness"
        node.stop_proof(route2, True)
        node.wait(done2.done)
        assert done2.result().status == GoalStatus.STATUS_SUCCEEDED
        node.x = 0.0
        route3 = node.route(3)
        _, moving3 = node.start(route3)
        node.wait(lambda: any(m.generation == 3 and m.twist.linear.x > 0 for m in node.raw))
        invalid = node.action.send_goal_async(
            FollowPath.Goal(path=route3.path, controller_id="missing_controller"))
        node.wait(invalid.done)
        invalid_result = invalid.result().get_result_async()
        node.wait(invalid_result.done)
        assert invalid_result.result().status == GoalStatus.STATUS_ABORTED
        node.wait(lambda: any(m.generation == 3 for m in node.cancels))
        node.pause(0.1)
        assert node.raw[-1].twist == Twist(), "Invalid preemption left the old controller running"
        assert len(node.plain) == 0, "Plain Twist output bypassed the tagged boundary"
        assert all(m.command_id and m.generation > 0 and m.map_epoch == "map" for m in node.raw)
        result.update(passed=True, tagged_commands=len(node.raw), plain_commands=len(node.plain),
                      cancel_status=done.result().status, goal_status=done2.result().status,
                      checks=["plugin route dispatch", "actual native tracker velocity", "tagged sole output",
                              "ROS action cancellation hook", "no late motion after stop",
                              "new owner after stop proof", "requested goal versus path endpoint",
                              "hold-only proof rejected", "measured-stop proof required",
                              "invalid controller preemption stops the old owner"])
    except Exception as error:
        result["error"] = repr(error)
        raise
    finally:
        (result_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        node.action.destroy()
        node.action = None
        node.destroy_node()
        rclpy.shutdown()
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        log.close()


if __name__ == "__main__":
    main()
