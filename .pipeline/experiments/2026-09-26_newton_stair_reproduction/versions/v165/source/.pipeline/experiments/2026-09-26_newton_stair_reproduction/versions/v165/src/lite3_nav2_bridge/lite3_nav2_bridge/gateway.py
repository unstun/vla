"""Standard NavigateToPose entry with exact P2B admission and physical-stop proof.

Nav2 owns navigation decisions. This gateway owns only identity, command gating
and the existing measured-stop contract. It never fabricates planning results.
"""
import copy
import math
from pathlib import Path
import threading
import time
from types import SimpleNamespace

import rclpy
from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path as RosPath
from std_srvs.srv import Trigger
from scan_planner_msgs.msg import P2BRoute, P2BCancel, P2BStopEvidence
from lite3_nav2_interfaces.srv import PlanRoute, BindRoute
from backend_adapter.applied_evidence import AppliedEvidenceReader, StopEvidenceConfig, StopEvidenceWindow
from backend_adapter.contracts import CommandIdentity, GateConfig, PlannerRequest
from backend_adapter.control_gate import CommandGate
from backend_adapter.pct_ipc import PctIpcClient, PctIpcClientConfig, PlannerRejected
from p2b_backend_ros.config import load_runtime_config
from p2b_backend_ros.node import RosScanPort


def finite_pose(pose):
    p, q = pose.position, pose.orientation
    return (all(math.isfinite(v) for v in (p.x, p.y, p.z, q.x, q.y, q.z, q.w))
            and abs(q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w - 1.0) < 1e-6)


class GuardedPort(RosScanPort):
    def __init__(self, node, config, gate):
        self.gateway = node
        super().__init__(node, config, gate)

    def _on_raw_command(self, msg):
        with self.gateway.lock:
            age_ns = self.node.get_clock().now().nanoseconds - (msg.stamp.sec * 1000000000 + msg.stamp.nanosec)
            if age_ns < 0 or age_ns > 100000000:
                self.gate.close('raw_command_source_stale')
                self._publish_zero()
                return
            super()._on_raw_command(msg)

    def _on_body_pose(self, msg):
        with self.gateway.lock:
            super()._on_body_pose(msg)

    def _watchdog_tick(self):
        with self.gateway.lock:
            super()._watchdog_tick()

    def _on_admission(self, msg):
        with self.gateway.lock:
            super()._on_admission(msg)
            current = self.gateway.binding
            if current is None:
                return
            identity = self._identity_from_msg(msg)
            if not identity.matches(self._identity_from_msg(current)):
                return
            if msg.consumer == 'fsm' and msg.status == 'accepted' and not self.gateway.stopping:
                if self.gate.owner is None:
                    self.gate.admit(identity)
                    self._mark_owner_admitted(identity)
            if (self.gateway.stopping and msg.consumer == 'controller' and msg.status == 'stopped'
                    and msg.hold_confirmed and self.gate.owner is not None):
                self.gate.confirm_consumer_hold(identity)


class MissionGateway(Node):
    def __init__(self):
        super().__init__('lite3_nav2_gateway')
        self.lock = threading.RLock()
        self.declare_parameter('config_path', '')
        path = self.get_parameter('config_path').value
        if not path:
            raise ValueError('An explicit versioned backend configuration is required')
        self.config = load_runtime_config(Path(path))
        if self.config['run_epoch_ns'] <= 0:
            raise ValueError('A unique positive execution epoch is required')
        self.frame = self.config['map']['frame_id']
        self.height = self.config['map']['nominal_body_height_m']
        self.goal = self.binding = self.ready = self.planned = None
        self.reserved = self.closing = self.stopping = False
        self.stop_verified_at = 0.0
        self.generation = 0
        self.last_released_route = None
        self.plan_bind_ready = self.plan_bind_reuse = False
        self.mission_id = ''
        self.request_id = self.goal_id = ''
        self.binding_goal = None
        self.path_heading = self.heading_resolved = False
        gate_config = dict(self.config['gate'])
        gate_config.pop('initial_heartbeat_grace_s', None)
        self.gate = CommandGate(GateConfig(**gate_config))
        self.port = GuardedPort(self, self.config, self.gate)
        applied = self.config['applied_evidence']
        if not applied['current_command_path']:
            raise ValueError('Applied-command evidence is mandatory; no odometry-only fallback')
        self.reader = AppliedEvidenceReader(Path(applied['current_command_path']))
        self.port.adapter = SimpleNamespace(applied_reader=self.reader)
        stop_fields = {k: applied[k] for k in ('stop_command_norm', 'stop_speed_mps',
                       'stop_yaw_rate_radps', 'stop_dwell_sim_seconds')}
        self.stop_window = StopEvidenceWindow(StopEvidenceConfig(**stop_fields))
        worker = self.config['pct_worker']
        self.pct = PctIpcClient(PctIpcClientConfig(**{k: worker[k] for k in
            ('host', 'port', 'connect_timeout_s', 'response_timeout_s')}))
        self.group = ReentrantCallbackGroup()
        self.binding_pub = self.create_publisher(P2BRoute, '/nav2_scan/route_binding', 10)
        self.proof_pub = self.create_publisher(P2BStopEvidence, '/nav2_scan/stop_evidence', 10)
        self.create_subscription(P2BRoute, '/nav2_scan/binding_ready', self.on_ready, 10)
        self.create_subscription(P2BCancel, '/p2b/scan_cancel', self.on_native_cancel, 10)
        self.create_service(PlanRoute, '/lite3_nav2/plan_route', self.plan_route, callback_group=self.group)
        self.create_service(BindRoute, '/lite3_nav2/bind_route', self.bind_route, callback_group=self.group)
        self.create_service(Trigger, '/lite3_nav2/wait_stopped', self.wait_stopped, callback_group=self.group)
        self.client = ActionClient(self, NavigateToPose, '/nav2_internal/navigate_to_pose', callback_group=self.group)
        self.server = ActionServer(self, NavigateToPose, '/navigate_to_pose', self.execute,
            goal_callback=self.accept_goal, cancel_callback=self.cancel_goal, callback_group=self.group)
        self.create_timer(0.02, self.stop_tick)
        self.declare_parameter('legacy_http',False)
        self.http = None
        if self.get_parameter('legacy_http').value:
            from .legacy_http import LegacyHttpPort
            self.http = LegacyHttpPort(self)

    def accept_goal(self, request):
        with self.lock:
            if (self.reserved or self.gate.owner is not None or self.binding is not None
                    or request.pose.header.frame_id != self.frame or not finite_pose(request.pose.pose)
                    or request.behavior_tree):
                self.get_logger().warning('Goal rejected: occupied owner, invalid frame/pose or external BT')
                return GoalResponse.REJECT
            try:
                self.port.measurement_provider()
                snapshot = self.reader.read()
                if snapshot.run_id != self.config['run_id'] or snapshot.run_epoch_ns != self.config['run_epoch_ns']:
                    self.get_logger().warning('Goal rejected: applied execution identity mismatch')
                    return GoalResponse.REJECT
            except Exception as exc:
                self.get_logger().warning('Goal rejected: ' + str(exc))
                return GoalResponse.REJECT
            self.reserved = True
            return GoalResponse.ACCEPT

    def cancel_goal(self, _handle):
        with self.lock:
            self.closing = True
            self.begin_stop('nav2_mission_cancel')
        return CancelResponse.ACCEPT

    def on_ready(self, msg):
        with self.lock:
            if self.binding is not None and msg == self.binding:
                self.ready = msg

    def on_native_cancel(self, msg):
        with self.lock:
            if self.binding is not None and self.port._identity_from_msg(msg).matches(
                    self.port._identity_from_msg(self.binding)):
                self.begin_stop(msg.reason)

    def begin_stop(self, reason):
        self.port._publish_zero()
        if self.binding is None or self.stopping:
            return
        self.stopping = True
        self.stop_verified_at = 0.0
        self.stop_window.reset(time.monotonic_ns())
        identity = self.port._identity_from_msg(self.binding)
        # Even a route cancelled before FSM admission must retain its owner until
        # controller hold and causal applied evidence are established.
        if self.gate.owner is None:
            self.gate.admit(identity)
        self.gate.request_cancel(identity, reason)
        msg = P2BCancel()
        self.port._fill_identity(msg, identity)
        msg.reason = reason
        self.port.cancel_pub.publish(msg)

    def stop_tick(self):
        with self.lock:
            if not self.stopping or self.binding is None or not self.gate.hold_ack:
                return
            try:
                self.port.measurement_provider()
                snapshot = self.reader.read()
                if not self.stop_window.observe(snapshot, self.config['run_id'], self.config['run_epoch_ns']):
                    return
            except Exception:
                return
            proof = P2BStopEvidence()
            stamp = self.port._last_odom_stamp_ns
            if stamp is None:
                return
            source_age = (self.get_clock().now().nanoseconds - stamp) / 1e9
            if source_age < 0.0 or source_age > 0.1:
                return
            proof.stamp.sec, proof.stamp.nanosec = divmod(stamp, 1000000000)
            self.port._fill_identity(proof.admission, self.port._identity_from_msg(self.binding))
            proof.admission.consumer = 'controller'
            proof.admission.status = 'stopped'
            proof.admission.message = 'causal_applied_stop_window'
            proof.admission.hold_confirmed = proof.admission.measured_stillness_confirmed = True
            self.proof_pub.publish(proof)
            self.stop_verified_at = time.monotonic()

    def stopped(self):
        return self.binding is None or time.monotonic() - self.stop_verified_at < 0.1

    def release(self):
        if not self.stopped():
            raise RuntimeError('Owner release requires fresh measured-stop proof')
        if self.binding is not None:
            self.last_released_route = (self.mission_id, self.binding.route_id, self.binding.generation)
        self.plan_bind_ready = self.plan_bind_reuse = False
        self.gate.owner = None
        self.gate.closed_reason = 'no_owner'
        self.gate.cancel_pending = self.gate.hold_ack = False
        self.binding = self.ready = None
        self.stopping = False

    def wait_stopped(self, _request, response):
        # Give real braking/settling the existing ten-second progress allowance.
        # This is a waiting budget, not a relaxation of the measured-stop proof.
        deadline = time.monotonic() + 10.0
        with self.lock:
            self.begin_stop('nav2_replan_wait')
        while time.monotonic() < deadline:
            with self.lock:
                if self.closing:
                    response.message = 'Mission is closing'
                    return response
                if self.stopped():
                    self.release()
                    response.success = True
                    return response
            time.sleep(0.01)
        response.message = 'Measured stop not established'
        return response

    def cached_reference_after_stop(self):
        if (self.planned is None or self.binding is not None or self.gate.owner is not None
                or self.closing or self.stopping):
            return False
        route = self.planned[1]
        return (self.last_released_route == (self.mission_id, route.route_id, self.generation)
                and route.goal_id == self.goal_id and route.frame_id == self.frame
                and route.map_epoch == self.config['map']['epoch']
                and route.map_revision == self.config['map']['revision'])

    def plan_route(self, request, response):
        try:
            with self.lock:
                if self.goal is None or self.closing or request.goal.pose != self.goal.pose or request.goal.header.frame_id != self.frame:
                    raise ValueError('No matching active mission')
                if request.start.header.frame_id != self.frame or not finite_pose(request.start.pose):
                    raise ValueError('Invalid PCT start')
                mission = self.mission_id
                start, target = request.start.pose.position, request.goal.pose.position
                layer = self.config['map'].get('pct_layer')
                query = PlannerRequest(self.request_id, self.goal_id, (start.x, start.y, start.z - self.height),
                    (target.x, target.y, target.z - self.height), self.frame,
                    self.config['map']['epoch'], self.config['map']['revision'], layer, layer, True)
                self.plan_bind_ready = self.plan_bind_reuse = False
            try:
                route = self.pct.plan(query)
            except PlannerRejected as exc:
                with self.lock:
                    # Nav2 may explicitly restore the original PCT reference.
                    # This is a binding permit, never a fabricated new route.
                    if (str(exc) == 'pct_no_route' and self.mission_id == mission
                            and self.cached_reference_after_stop()):
                        self.plan_bind_ready = self.plan_bind_reuse = True
                raise
            with self.lock:
                if self.mission_id != mission or self.closing or self.goal is None:
                    raise ValueError('Discarded late PCT result')
                path = RosPath()
                path.header.frame_id = self.frame
                path.header.stamp = self.get_clock().now().to_msg()
                for x, y, z in route.waypoints_m:
                    pose = PoseStamped()
                    pose.header = copy.deepcopy(path.header)
                    pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = x, y, z
                    pose.pose.orientation.w = 1.0
                    path.poses.append(pose)
                self.planned = (copy.deepcopy(path), route)
                self.plan_bind_ready = True
                self.plan_bind_reuse = False
                if self.path_heading and not self.heading_resolved:
                    end = route.waypoints_m[-1]
                    for point in reversed(route.waypoints_m[:-1]):
                        dx,dy = end[0]-point[0],end[1]-point[1]
                        if math.hypot(dx,dy)>1e-6:
                            yaw = math.atan2(dy,dx)
                            self.binding_goal.orientation.z = math.sin(yaw/2)
                            self.binding_goal.orientation.w = math.cos(yaw/2)
                            self.heading_resolved = True
                            break
                    if not self.heading_resolved: raise ValueError('Native PCT path cannot define requested heading')
                response.path = path
                response.accepted = True
        except Exception as exc:
            response.message = str(exc)
        return response

    def bind_route(self, request, response):
        try:
            with self.lock:
                if (self.goal is None or self.closing or request.goal.pose != self.goal.pose
                        or self.planned is None or request.path != self.planned[0] or self.binding is not None
                        or not self.plan_bind_ready):
                    raise ValueError('Unplanned path, active prior owner, or closing mission')
                route = self.planned[1]
                reuse = self.plan_bind_reuse
                if reuse and not self.cached_reference_after_stop():
                    raise ValueError('Cached reference no longer matches a released owner')
                self.plan_bind_ready = self.plan_bind_reuse = False
                self.generation += 1
                if reuse:
                    self.get_logger().warning('V163_REFERENCE_REUSED route=' + route.route_id
                        + ' generation=' + str(self.generation))
                binding = P2BRoute()
                identity = CommandIdentity(self.config['run_id'], self.config['run_epoch_ns'],
                    self.request_id, self.goal_id, route.route_id, 'cmd-' + str(self.generation),
                    self.generation, route.map_epoch, route.map_revision)
                self.port._fill_identity(binding, identity)
                binding.path = copy.deepcopy(request.path)
                binding.path.header.stamp = self.get_clock().now().to_msg()
                for pose in binding.path.poses: pose.header = copy.deepcopy(binding.path.header)
                binding.has_goal_pose = True
                binding.goal_pose = copy.deepcopy(self.binding_goal)
                self.binding, self.ready = binding, None
                self.binding_pub.publish(binding)
            deadline = time.monotonic() + 1.5
            next_publish = time.monotonic() + 0.1
            while time.monotonic() < deadline:
                with self.lock:
                    if self.closing or self.binding != binding:
                        raise ValueError('Binding revoked')
                    if self.ready == binding:
                        response.binding = binding
                        response.accepted = True
                        return response
                    if time.monotonic() >= next_publish:
                        self.binding_pub.publish(binding)
                        next_publish = time.monotonic() + 0.1
                time.sleep(0.01)
            raise TimeoutError('Exact controller binding acknowledgment missing')
        except Exception as exc:
            response.message = str(exc)
        return response

    def await_future(self, future, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and rclpy.ok():
            if future.done(): return future.result()
            time.sleep(0.01)
        raise TimeoutError('Nav2 action deadline')

    def execute(self, handle):
        inner = None
        status = 6
        try:
            with self.lock:
                self.goal = copy.deepcopy(handle.request.pose)
                self.mission_id = 'goal-' + bytes(handle.goal_id.uuid).hex()
                self.request_id = self.goal_id = self.mission_id
                self.binding_goal = copy.deepcopy(self.goal.pose)
                self.path_heading = self.heading_resolved = False
                context = self.http.contexts.pop(bytes(handle.goal_id.uuid).hex(),None) if self.http else None
                if context is not None:
                    if context['pose'] != handle.request.pose: raise ValueError('Legacy goal context mismatch')
                    self.request_id,self.goal_id = context['request_id'],context['goal_id']
                    self.path_heading = context['path_heading']
                # A cancellation may arrive before this execute callback.
                if self.closing or handle.is_cancel_requested:
                    raise RuntimeError('Mission cancelled before dispatch')
            if not self.client.wait_for_server(timeout_sec=3.0):
                raise RuntimeError('Nav2 navigator unavailable')
            inner = self.await_future(self.client.send_goal_async(handle.request,
                feedback_callback=lambda feedback: handle.publish_feedback(feedback.feedback)), 3.0)
            if not inner.accepted:
                raise RuntimeError('Nav2 navigator rejected goal')
            result = inner.get_result_async()
            cancelled = False
            deadline = time.monotonic() + self.config['service']['command_timeout_s']
            while not result.done() and time.monotonic() < deadline:
                if handle.is_cancel_requested and not cancelled:
                    inner.cancel_goal_async()
                    cancelled = True
                time.sleep(0.01)
            if not result.done():
                inner.cancel_goal_async()
                raise TimeoutError('Navigation mission deadline')
            status = result.result().status
        except Exception as exc:
            self.get_logger().error(str(exc))
            if inner is not None and inner.accepted:
                inner.cancel_goal_async()
        finally:
            with self.lock:
                self.closing = True
                self.begin_stop('nav2_mission_terminal')
            end = time.monotonic() + 5.0
            while time.monotonic() < end:
                with self.lock:
                    if self.stopped(): break
                time.sleep(0.01)
            with self.lock:
                stop_ok = self.stopped()
                if stop_ok:
                    self.release()
                    self.goal = self.planned = None
                    self.reserved = self.closing = False
                # A failed stop latches admission closed; it is never converted
                # into a successful cancellation or permission for another goal.
                if stop_ok and handle.is_cancel_requested: handle.canceled()
                elif stop_ok and status == 4: handle.succeed()
                else: handle.abort()
        return NavigateToPose.Result()


def main():
    rclpy.init()
    node = MissionGateway()
    executor = MultiThreadedExecutor(num_threads=6)
    executor.add_node(node)
    try:
        executor.spin()
    finally:
        with node.lock:
            node.closing = True
            node.begin_stop('gateway_shutdown')
        executor.shutdown()
        if node.http: node.http.close()
        node.server.destroy()
        node.client.destroy()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
