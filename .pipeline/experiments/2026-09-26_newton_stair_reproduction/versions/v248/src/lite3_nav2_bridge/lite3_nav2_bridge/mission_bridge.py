"""HTTP task adapter: submit, cancel and observe the Nav2 action."""
import copy
import json
import math
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import rclpy
from nav2_msgs.action import NavigateToPose
from lite3_nav2_interfaces.srv import RouteSession
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.clock import Clock, ClockType
from lifecycle_msgs.srv import GetState
from lifecycle_msgs.msg import State
from .runtime_failure import read_json, valid_failure, process_failure
from rclpy.qos import qos_profile_sensor_data


def finite_values(values):
    return all(not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)
               for v in values)


def set_yaw(pose, yaw):
    pose.orientation.x = pose.orientation.y = 0.0
    pose.orientation.z = math.sin(yaw / 2.0)
    pose.orientation.w = math.cos(yaw / 2.0)


class MissionBridge(Node):
    def __init__(self):
        super().__init__('lite3_nav2_mission_bridge')
        config_path = self.declare_parameter('config_path', '').value
        odom_topic = self.declare_parameter('odom_topic', '/quad_0/body_pose').value
        with open(config_path, encoding='utf-8') as stream:
            self.config = json.load(stream)
        self.config.setdefault('run_id', '')
        self.config.setdefault('run_epoch_ns', 0)
        self.frame_id = 'world'
        self.reference_height_m = float(self.config.get('map', {}).get('nominal_body_height_m', 0.35))
        if not math.isfinite(self.reference_height_m):
            raise ValueError('nominal_body_height_m must be finite')
        self._lock = threading.RLock()
        self.jobs = {}
        self.terminal_results = []
        self.current_owner = None
        self.measurement_body_pose = None
        self._handles = {}
        self._dispatch = []
        self._session_pending = None
        self._seq = 0
        self._native_failure = None
        self._failure_path = self.declare_parameter('native_process_failure_path', '').value
        self._critical_timeout = float(self.declare_parameter('critical_liveness_timeout_s', 0.0).value)
        if (not math.isfinite(self._critical_timeout) or self._critical_timeout<0
                or (self._critical_timeout>0 and not self._failure_path)):
            raise ValueError('Invalid critical-process health configuration')
        self._health_pending, self._health_last = {}, {}
        self._lifecycle_state = {}
        self._require_active_navigation = bool(self.declare_parameter('require_active_navigation', False).value)

        self._input_group = ReentrantCallbackGroup()
        self._client = ActionClient(self, NavigateToPose, '/nav2_internal/navigate_to_pose',
                                    callback_group=self._input_group)
        self._odom_sub = self.create_subscription(Odometry, odom_topic, self.on_odometry,
                                                  qos_profile_sensor_data,
                                                  callback_group=self._input_group)
        # HTTP threads only update the queue; ROS action calls run on the executor.
        self._session_client = self.create_client(RouteSession, '/lite3_nav2/route_session',
                                                  callback_group=self._input_group)
        self._dispatch_timer = self.create_timer(0.02, self.dispatch_goals)
        self._liveness_clients = {name:self.create_client(GetState,name+'/get_state',callback_group=self._input_group)
            for name in ('/controller_server','/planner_server','/recoveries_server','/nav2_internal/bt_navigator')} if self._critical_timeout>0 or self._require_active_navigation else {}
        self._fault_timer = self.create_timer(0.02,self._check_native_health,
            clock=Clock(clock_type=ClockType.STEADY_TIME))

        http = self.config.get('http', {})
        self._http = ThreadingHTTPServer((http.get('host', '127.0.0.1'), int(http.get('port', 8785))),
                                         self._handler_type())
        self._http_thread = threading.Thread(target=self._http.serve_forever, daemon=True)
        self._http_thread.start()

    def _check_native_health(self):
        with self._lock:
            fault=read_json(self._failure_path) if self._failure_path else None
            if valid_failure(fault,self.config.get('run_id'),self.config.get('run_epoch_ns')):
                self._native_failure=fault
                for rid,job in self.jobs.items():
                    if job['status'] in ('pending','running'):
                        handle=self._handles.get(rid)
                        if handle:
                            try: handle.cancel_goal_async()
                            except Exception: pass
                        self._finish(rid,'failed',fault['cause'],dict(fault))
                return
            active=self.current_owner and self.jobs[self.current_owner['request_id']]['status'] in ('pending','running')
            if not active:
                self._health_last.clear()
                return
            running=self.jobs[self.current_owner['request_id']]['status']=='running'
            now=time.monotonic()
            for name,client in self._liveness_clients.items():
                self._health_last.setdefault(name,now)
                pending=self._health_pending.get(name)
                if pending and pending.done():
                    try:
                        if pending.result() is not None:
                            self._health_last[name]=now
                            self._lifecycle_state[name]=(int(pending.result().current_state.id),now)
                    except Exception: pass
                    self._health_pending.pop(name,None)
                if running and self._critical_timeout>0 and now-self._health_last[name]>self._critical_timeout:
                    process_failure(self._failure_path,self.config['run_id'],self.config['run_epoch_ns'],
                                    name,None,'native_node_unresponsive')
                    return
                if name not in self._health_pending and client.service_is_ready():
                    try:self._health_pending[name]=client.call_async(GetState.Request())
                    except Exception: pass

    def _inactive_navigation(self, now):
        if not self._require_active_navigation:
            return {}
        return {name: self._lifecycle_state.get(name, (None, None))[0]
                for name in self._liveness_clients
                if name not in self._lifecycle_state
                or self._lifecycle_state[name][0] != State.PRIMARY_STATE_ACTIVE
                or now - self._lifecycle_state[name][1] > 1.0}

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
            if self._native_failure:
                raise ValueError('Native navigation unavailable: '+self._native_failure['component'])
            body_xyz = [float(xyz[0]), float(xyz[1]), float(xyz[2]) + self.reference_height_m]
            self.jobs[request_id] = {'request_id': request_id, 'goal_id': goal_id, 'status': 'pending',
                'target_body_xyz': body_xyz, 'cancel_requested': False,
                'session_id': '%s/%s/%s' % (self.config.get('run_id', ''), self.config.get('run_epoch_ns', 0), request_id),
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
                if not self._client.server_is_ready() or not self._session_client.service_is_ready():
                    if time.monotonic() - job['submitted_s'] > 5.0:
                        self._finish(request_id, 'failed', 'nav2_action_server_unavailable', {})
                    else:
                        self._dispatch.append(request_id)
                    continue
                inactive = self._inactive_navigation(time.monotonic())
                if inactive:
                    if time.monotonic() - job['submitted_s'] > 5.0:
                        self._finish(request_id, 'failed', 'nav2_nodes_not_active', {'nodes': inactive})
                    else:
                        self._dispatch.append(request_id)
                    continue
                if self._require_active_navigation:
                    job['navigation_active'] = {name: {'state_id': state, 'observed_monotonic_s': stamp}
                                                for name, (state, stamp) in self._lifecycle_state.items()}
                    self.get_logger().info('navigation_active_before_goal ' + json.dumps({'request_id': request_id, 'nodes': job['navigation_active']}))
                goal = NavigateToPose.Goal()
                goal.pose.header.frame_id = self.frame_id
                goal.pose.header.stamp = self.get_clock().now().to_msg()
                goal.pose.pose.position.x, goal.pose.pose.position.y, goal.pose.pose.position.z = job['target_body_xyz']
                yaw = job['data'].get('target_yaw_rad')
                set_yaw(goal.pose.pose, float(yaw) if yaw is not None else 0.0)
                # One metadata handshake per task, never a planning call.
                if self._session_pending is not None:
                    self._dispatch.append(request_id)
                    continue
                request = RouteSession.Request()
                request.operation = request.BEGIN
                request.session_id = job['session_id']
                request.goal = goal.pose
                request.infer_heading = yaw is None
                self._session_pending = request_id
                try:
                    self._session_client.call_async(request).add_done_callback(
                        lambda future, rid=request_id, target=goal: self._session_ready(rid, target, future))
                except Exception as exc:
                    self._session_pending = None
                    self._finish(request_id, 'failed', 'nav2_session_failed', {'error': str(exc)})

    def _end_session(self, job):
        request = RouteSession.Request()
        request.operation = request.END
        request.session_id = job['session_id']
        self._session_client.call_async(request)

    def _session_ready(self, request_id, goal, future):
        with self._lock:
            self._session_pending = None
            job = self.jobs[request_id]
            try:
                result = future.result()
                if not result.accepted:
                    raise ValueError(result.message)
                if (job['cancel_requested'] or job['status'] not in ('pending', 'running') or
                        not self.current_owner or self.current_owner['request_id'] != request_id):
                    self._end_session(job)
                    if job['status'] in ('pending', 'running'):
                        self._finish(request_id, 'cancelled', 'cancelled_before_dispatch', {})
                    return
                job['sent'] = True
                self._client.send_goal_async(goal).add_done_callback(
                    lambda accepted, rid=request_id: self._accepted(rid, accepted))
            except Exception as exc:
                self._finish(request_id, 'failed', 'nav2_session_failed', {'error': str(exc)})

    def _accepted(self, request_id, future):
        with self._lock:
            try:
                handle = future.result()
                if not handle.accepted:
                    self._finish(request_id, 'failed', 'nav2_goal_rejected', {})
                    return
                job=self.jobs[request_id]
                if (job['status'] not in ('pending','running') or not self.current_owner
                        or self.current_owner['request_id']!=request_id):
                    handle.cancel_goal_async()
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
        try:
            self._end_session(job)
        except Exception as exc:
            data=dict(data,session_cleanup_error=str(exc))
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
            jobs = copy.deepcopy(self.jobs)
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
        self.destroy_client(self._session_client)
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
