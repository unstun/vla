"""HTTP missions backed by Nav2 and an in-process PCT Path service."""
import copy
import json
import math
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path as FilePath

import rclpy
from geometry_msgs.msg import PoseStamped
from lite3_nav2_interfaces.srv import PlanRoute
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry, Path
from rclpy.action import ActionClient
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data


def finite_values(values):
    return all(not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)
               for v in values)


def valid_orientation(q):
    return finite_values((q.x, q.y, q.z, q.w)) and abs(
        q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w - 1.0) <= 1e-6


def set_yaw(pose, yaw):
    pose.orientation.x = pose.orientation.y = 0.0
    pose.orientation.z = math.sin(yaw / 2.0)
    pose.orientation.w = math.cos(yaw / 2.0)


class MissionBridge(Node):
    def __init__(self):
        super().__init__('lite3_nav2_mission_bridge')
        config_path = self.declare_parameter('config_path', '').value
        pct_map = self.declare_parameter('pct_map', '').value
        odom_topic = self.declare_parameter('odom_topic', '/quad_0/body_pose').value
        with open(config_path, encoding='utf-8') as stream:
            self.config = json.load(stream)
        self.frame_id = 'world'
        self.reference_height_m = float(self.config.get('map', {}).get('nominal_body_height_m', 0.35))
        if not math.isfinite(self.reference_height_m):
            raise ValueError('nominal_body_height_m must be finite')
        self._lock = threading.RLock()
        self._planner_lock = threading.Lock()
        self.jobs = {}
        self.terminal_results = []
        self.current_owner = None
        self.measurement_body_pose = None
        self._handles = {}
        self._dispatch = []
        self._seq = 0
        self._load_planner(pct_map)
        self._planning_group = MutuallyExclusiveCallbackGroup()
        self._input_group = ReentrantCallbackGroup()
        self._client = ActionClient(self, NavigateToPose, '/nav2_internal/navigate_to_pose',
                                    callback_group=self._input_group)
        self._path_pub = self.create_publisher(Path, '/pct_planned_path', QoSProfile(
            depth=10, reliability=ReliabilityPolicy.RELIABLE))
        self._plan_service = self.create_service(PlanRoute, '/lite3_nav2/plan_route', self.plan_route,
                                                callback_group=self._planning_group)
        self._odom_sub = self.create_subscription(Odometry, odom_topic, self.on_odometry,
                                                  qos_profile_sensor_data,
                                                  callback_group=self._input_group)
        # HTTP threads only update the queue; ROS action calls run on the executor.
        self._dispatch_timer = self.create_timer(0.02, self.dispatch_goals)
        http = self.config.get('http', {})
        self._http = ThreadingHTTPServer((http.get('host', '127.0.0.1'), int(http.get('port', 8785))),
                                         self._handler_type())
        self._http_thread = threading.Thread(target=self._http.serve_forever, daemon=True)
        self._http_thread.start()

    def _load_planner(self, pct_map):
        import pct_planner
        root = str(FilePath(pct_planner.__file__).resolve().parents[1])
        if root not in sys.path:
            sys.path.insert(0, root)
        from pct_planner.config import Config
        from pct_planner.planner_wrapper import TomogramPlanner
        path = FilePath(pct_map).expanduser().resolve(strict=True)
        self._planner = TomogramPlanner(Config(), str(path.parent))
        self._planner.loadTomogram(tomo_file='', tomogram_path=str(path))
        if hasattr(self._planner.planner, 'set_reference_height'):
            self._planner.planner.set_reference_height(self.reference_height_m)

    def plan_route(self, request, response):
        try:
            for label, pose in (('start', request.start), ('goal', request.goal)):
                p, q = pose.pose.position, pose.pose.orientation
                if pose.header.frame_id != self.frame_id or not finite_values((p.x, p.y, p.z, q.x, q.y, q.z, q.w)):
                    raise ValueError(label + ' must have finite coordinates in world')
            start, goal = request.start.pose.position, request.goal.pose.position
            with self._lock:
                owner = self.current_owner
                job = self.jobs.get(owner['request_id']) if owner else None
                targets = [job['target_body_xyz']] if job else []
                if job and job.get('canonical_goal_pose') is not None:
                    p = job['canonical_goal_pose'].position
                    targets.append((p.x, p.y, p.z))
                matches_goal = job and any(all(abs(a-b) <= 1e-6 for a, b in zip(
                    (goal.x, goal.y, goal.z), target)) for target in targets)
                job = job if matches_goal and job['status'] in ('pending', 'running') and not job['cancel_requested'] else None
            with self._planner_lock:
                raw = self._planner.plan([start.x, start.y, start.z], [goal.x, goal.y, goal.z],
                                         start_layer=None, end_layer=None, optimize=True)
                if raw is None:
                    raise ValueError('pct_no_route')
                optimizer = (self._planner.planner.get_trajectory_optimizer_wnoj()
                             if self._planner.use_quintic else
                             self._planner.planner.get_trajectory_optimizer())
                heights = optimizer.get_heights()
                if hasattr(raw, 'tolist'):
                    raw = raw.tolist()
                if hasattr(heights, 'tolist'):
                    heights = heights.tolist()
                heights = [float(h[0] if isinstance(h, (list, tuple)) else h) for h in heights]
            if len(raw) < 2 or len(raw) != len(heights):
                raise ValueError('pct_height_count_mismatch_or_empty_route')
            points = [(float(p[0]), float(p[1]), h) for p, h in zip(raw, heights)]
            if not all(finite_values(p) for p in points):
                raise ValueError('pct_nonfinite_route')
            path = Path()
            path.header.frame_id = self.frame_id
            path.header.stamp = self.get_clock().now().to_msg()
            yaw = 0.0
            for i, point in enumerate(points):
                if i + 1 < len(points):
                    dx, dy = points[i+1][0] - point[0], points[i+1][1] - point[1]
                    if math.hypot(dx, dy) > 1e-12:
                        yaw = math.atan2(dy, dx)
                pose = PoseStamped()
                pose.header = copy.deepcopy(path.header)
                pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = point
                set_yaw(pose.pose, yaw)
                path.poses.append(pose)
            q = request.goal.pose.orientation
            with self._lock:
                if job is not None:
                    if (self.current_owner != owner or job['status'] not in ('pending', 'running')
                            or job['cancel_requested']):
                        raise ValueError('mission_changed_during_planning')
                    canonical = job.get('canonical_goal_pose')
                    if canonical is None:
                        canonical = copy.deepcopy(path.poses[-1].pose)
                        target_yaw = job['data'].get('target_yaw_rad')
                        if target_yaw is None:
                            for a, b in reversed(list(zip(points, points[1:]))):
                                dx, dy = b[0]-a[0], b[1]-a[1]
                                if math.hypot(dx, dy) > 1e-6:
                                    target_yaw = math.atan2(dy, dx)
                                    break
                            if target_yaw is None:
                                raise ValueError('pct_no_terminal_heading')
                        set_yaw(canonical, float(target_yaw))
                    # PCT may move its final sample across replans. Bind the entire
                    # terminal pose, but reject a disconnected final connector.
                    a, b = path.poses[-2].pose.position, canonical.position
                    step = math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2 + (a.z-b.z)**2)
                    if not math.isfinite(step) or step > 2.0:
                        raise ValueError('pct_canonical_goal_disconnected')
                    path.poses[-1].pose = copy.deepcopy(canonical)
                    job['canonical_goal_pose'] = copy.deepcopy(canonical)
                    # Evidence/cache only: a failed new PCT plan remains a failure.
                    job['cached_path'] = copy.deepcopy(path)
                elif abs(q.x) + abs(q.y) + abs(q.z) > 1e-12:
                    if not valid_orientation(q):
                        raise ValueError('goal orientation must be a normalized quaternion')
                    path.poses[-1].pose.orientation = copy.deepcopy(q)
                response.path = path
                response.accepted = True
                response.message = 'planned'
                self._path_pub.publish(path)
        except Exception as exc:
            response.accepted = False
            response.message = str(exc)
            self.get_logger().error('PCT planning failed: ' + str(exc))
        return response

    def on_odometry(self, message):
        p, q = message.pose.pose.position, message.pose.pose.orientation
        v, w = message.twist.twist.linear, message.twist.twist.angular
        body = {'frame_id': message.header.frame_id,
                'stamp_ns': message.header.stamp.sec * 1000000000 + message.header.stamp.nanosec,
                'x': p.x, 'y': p.y, 'z': p.z,
                'roll_rad': math.atan2(2*(q.w*q.x + q.y*q.z), 1-2*(q.x*q.x + q.y*q.y)),
                'pitch_rad': math.asin(max(-1.0, min(1.0, 2*(q.w*q.y - q.z*q.x)))),
                'yaw_rad': math.atan2(2*(q.w*q.z + q.x*q.y), 1-2*(q.y*q.y + q.z*q.z)),
                'vx': v.x, 'vy': v.y, 'vz': v.z, 'wx': w.x, 'wy': w.y, 'wz': w.z}
        with self._lock:
            self.measurement_body_pose = body

    def submit_goal(self, payload):
        request_id, goal_id = payload.get('request_id'), payload.get('goal_id')
        xyz = payload.get('target_ground_xyz')
        if not isinstance(request_id, str) or not request_id or not isinstance(goal_id, str) or not goal_id:
            raise ValueError('request_id and goal_id must be nonempty strings')
        if not isinstance(xyz, list) or len(xyz) != 3 or not finite_values(xyz):
            raise ValueError('target_ground_xyz must have three finite coordinates')
        if payload.get('frame') != self.frame_id:
            raise ValueError('goal frame must be world')
        if 'map_epoch' not in payload or 'map_revision' not in payload:
            raise ValueError('map_epoch and map_revision are required')
        yaw = payload.get('target_yaw_rad')
        if yaw is not None and not finite_values((yaw,)):
            raise ValueError('target_yaw_rad must be finite')
        with self._lock:
            if request_id in self.jobs:
                if self.jobs[request_id]['data'] != payload:
                    raise ValueError('request_id already used for a different goal')
                return {'ok': True, 'request_id': request_id, 'status': self.jobs[request_id]['status']}
            body_xyz = [float(xyz[0]), float(xyz[1]), float(xyz[2]) + self.reference_height_m]
            self.jobs[request_id] = {'request_id': request_id, 'goal_id': goal_id, 'status': 'pending',
                'path_heading': yaw is None, 'target_body_xyz': body_xyz, 'cancel_requested': False,
                'canonical_goal_pose': None, 'cached_path': None,
                'submitted_s': time.monotonic(), 'sent': False, 'data': copy.deepcopy(payload)}
            self.current_owner = {'request_id': request_id, 'goal_id': goal_id}
            self._dispatch.append(request_id)
        return {'ok': True, 'request_id': request_id, 'status': 'pending'}

    def cancel_goal(self, payload):
        if not isinstance(payload.get('request_id'), str) or not payload['request_id']:
            raise ValueError('cancel request_id is required')
        target = payload.get('target_request_id')
        if not isinstance(target, str) or not target:
            raise ValueError('target_request_id is required')
        with self._lock:
            job = self.jobs.get(target)
            if job is None:
                return {'ok': False, 'status': 'not_found', 'target_request_id': target}
            if job['status'] in ('pending', 'running'):
                job['cancel_requested'] = True
                if target not in self._dispatch:
                    self._dispatch.append(target)
                status = 'cancelling'
            else:
                status = job['status']
            return {'ok': True, 'status': status, 'target_request_id': target}

    def dispatch_goals(self):
        with self._lock:
            queued, self._dispatch = self._dispatch, []
            for request_id in queued:
                job = self.jobs[request_id]
                if job['status'] not in ('pending', 'running'):
                    continue
                if job['cancel_requested']:
                    handle = self._handles.get(request_id)
                    if handle:
                        handle.cancel_goal_async().add_done_callback(
                            lambda future, rid=request_id: self._cancel_response(rid, future))
                    elif not job['sent']:
                        self._finish(request_id, 'cancelled', 'cancelled_before_dispatch', {})
                    # If acceptance is outstanding, _accepted will dispatch the cancel.
                    continue
                if job['sent']:
                    continue
                if not self._client.server_is_ready():
                    if time.monotonic() - job['submitted_s'] > 5.0:
                        self._finish(request_id, 'failed', 'nav2_action_server_unavailable', {})
                    else:
                        self._dispatch.append(request_id)
                    continue
                goal = NavigateToPose.Goal()
                goal.pose.header.frame_id = self.frame_id
                goal.pose.header.stamp = self.get_clock().now().to_msg()
                goal.pose.pose.position.x, goal.pose.pose.position.y, goal.pose.pose.position.z = job['target_body_xyz']
                yaw = job['data'].get('target_yaw_rad')
                set_yaw(goal.pose.pose, float(yaw) if yaw is not None else 0.0)
                if job['canonical_goal_pose'] is not None:
                    goal.pose.pose = copy.deepcopy(job['canonical_goal_pose'])
                try:
                    job['sent'] = True
                    self._client.send_goal_async(goal).add_done_callback(
                        lambda future, rid=request_id: self._accepted(rid, future))
                except Exception as exc:
                    self._finish(request_id, 'failed', 'nav2_send_failed', {'error': str(exc)})

    def _accepted(self, request_id, future):
        with self._lock:
            try:
                handle = future.result()
                if not handle.accepted:
                    self._finish(request_id, 'failed', 'nav2_goal_rejected', {})
                    return
                self._handles[request_id] = handle
                self.jobs[request_id]['status'] = 'running'
                handle.get_result_async().add_done_callback(
                    lambda result, rid=request_id: self._completed(rid, result))
                if self.jobs[request_id]['cancel_requested']:
                    self._dispatch.append(request_id)
            except Exception as exc:
                self._finish(request_id, 'failed', 'nav2_accept_failed', {'error': str(exc)})

    def _cancel_response(self, request_id, future):
        try:
            response = future.result()
            with self._lock:
                self.jobs[request_id]['cancel_accepted'] = bool(response.goals_canceling)
        except Exception as exc:
            self.get_logger().error('Nav2 cancel failed: ' + str(exc))

    def _completed(self, request_id, future):
        with self._lock:
            try:
                result = future.result()
                status = {4: 'arrived', 5: 'cancelled'}.get(result.status, 'failed')
                self._finish(request_id, status, 'nav2_' + status, {'action_status': result.status})
            except Exception as exc:
                self._finish(request_id, 'failed', 'nav2_result_failed', {'error': str(exc)})

    def _finish(self, request_id, status, cause, data):
        job = self.jobs[request_id]
        if job['status'] not in ('pending', 'running'):
            return
        job['status'], job['cause'] = status, cause
        self._seq += 1
        self.terminal_results.append({'seq': self._seq, 'request_id': request_id,
            'goal_id': job['goal_id'], 'status': status, 'cause': cause,
            'monotonic_ns': time.monotonic_ns(), 'data': data})
        self._handles.pop(request_id, None)
        if self.current_owner and self.current_owner['request_id'] == request_id:
            self.current_owner = None

    def get_state(self):
        with self._lock:
            body = copy.deepcopy(self.measurement_body_pose)
            # ROS messages stay internal; the HTTP status remains JSON serializable.
            jobs = {key: copy.deepcopy({k: v for k, v in job.items()
                                       if k not in ('canonical_goal_pose', 'cached_path')})
                    for key, job in self.jobs.items()}
            for key, job in self.jobs.items():
                pose = job['canonical_goal_pose']
                jobs[key]['canonical_goal_pose'] = None if pose is None else {
                    'position': {axis: getattr(pose.position, axis) for axis in ('x', 'y', 'z')},
                    'orientation': {axis: getattr(pose.orientation, axis) for axis in ('x', 'y', 'z', 'w')}}
                jobs[key]['cached_path_available'] = job['cached_path'] is not None
            return {'run_id': self.config.get('run_id', ''),
                'run_epoch_ns': int(self.config.get('run_epoch_ns', 0)),
                'readiness': {'body_pose_ready': body is not None,
                    'applied_snapshot': {'configured': True, 'ready': True}, 'last_error': None},
                'measurement_body_pose': body, 'service': {'current_owner': copy.deepcopy(self.current_owner)},
                'jobs': jobs, 'terminal_results': copy.deepcopy(self.terminal_results),
                'navigation_authority': 'Nav2', 'monotonic_s': time.monotonic()}

    def _handler_type(self):
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def respond(self, status, payload):
                data = json.dumps(payload, allow_nan=False).encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self.respond(200, bridge.get_state()) if self.path == '/state' else self.respond(
                    404, {'ok': False, 'error': 'not_found'})

            def do_POST(self):
                if self.path not in ('/goal', '/cancel'):
                    self.respond(404, {'ok': False, 'error': 'not_found'})
                    return
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= 65536:
                        raise ValueError('JSON body must be between 1 and 65536 bytes')
                    payload = json.loads(self.rfile.read(length))
                    if not isinstance(payload, dict):
                        raise ValueError('JSON body must be an object')
                    result = bridge.submit_goal(payload) if self.path == '/goal' else bridge.cancel_goal(payload)
                    self.respond(200, result)
                except (ValueError, TypeError, KeyError) as exc:
                    self.respond(400, {'ok': False, 'error': str(exc)})
        return Handler

    def destroy_node(self):
        self._http.shutdown()
        self._http.server_close()
        self._http_thread.join(timeout=2.0)
        self._client.destroy()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    executor = MultiThreadedExecutor(num_threads=3)
    try:
        node = MissionBridge()
        executor.add_node(node)
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
