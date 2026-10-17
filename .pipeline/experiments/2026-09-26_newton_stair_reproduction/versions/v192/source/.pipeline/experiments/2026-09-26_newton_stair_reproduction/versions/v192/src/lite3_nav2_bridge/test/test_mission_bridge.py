"""Loopback HTTP/ROS tests; PCT's native optimizer is replaced by a deterministic fixture."""
import json
import math
import threading
import time
import urllib.error
import urllib.request
from unittest.mock import patch

import pytest
import rclpy
from geometry_msgs.msg import PoseStamped
from lite3_nav2_interfaces.srv import PlanRoute
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry, Path
from rclpy.action import ActionServer, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import qos_profile_sensor_data

from lite3_nav2_bridge.mission_bridge import MissionBridge


class Planner:
    use_quintic = False

    def __init__(self):
        self.planner = self
        self.heights = [[0.35], [0.45], [0.55]]
        self.calls = []

    def plan(self, start, goal, **kwargs):
        self.calls.append((start, goal, kwargs))
        return [[0.0, 0.0, 0.85], [1.0, 0.0, 0.95], [1.0, 1.0, 1.05]]

    def get_trajectory_optimizer(self):
        return self

    def get_trajectory_optimizer_wnoj(self):
        return self

    def get_heights(self):
        return self.heights


def wait(predicate, seconds=4.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        value = predicate()
        if value:
            return value
        time.sleep(0.01)
    raise AssertionError('Timed out waiting for loopback ROS operation')


@pytest.fixture
def bridge(tmp_path):
    config = tmp_path / 'backend.json'
    config.write_text(json.dumps({'run_id': 'unit', 'run_epoch_ns': 42,
        'map': {'nominal_body_height_m': 0.35}, 'http': {'host': '127.0.0.1', 'port': 0}}))
    rclpy.init(args=['--ros-args', '-p', 'config_path:=' + str(config)])
    def load(node, _):
        node._planner = Planner()
    with patch.object(MissionBridge, '_load_planner', load):
        node = MissionBridge()
    io = rclpy.create_node('mission_test_io')
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    executor.add_node(io)
    stop = threading.Event()
    node._test_action_servers = []
    def spin():
        while not stop.is_set():
            executor.spin_once(timeout_sec=0.05)
    thread = threading.Thread(target=spin, daemon=True)
    thread.start()
    try:
        yield node, io
    finally:
        # Foxy must leave its wait set before an action server is destroyed.
        stop.set()
        thread.join(timeout=3)
        assert not thread.is_alive()
        executor.shutdown()
        for server in node._test_action_servers:
            server.destroy()
        node.destroy_node()
        io.destroy_node()
        rclpy.shutdown()


def http(node, endpoint, data=None):
    url = 'http://127.0.0.1:%d%s' % (node._http.server_port, endpoint)
    request = urllib.request.Request(url, data=None if data is None else json.dumps(data).encode(),
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=2) as response:
        return json.load(response)


def goal_payload(request_id='request', **kwargs):
    return dict(request_id=request_id, goal_id='goal-' + request_id, target_ground_xyz=[1.0, 1.0, 0.2],
                frame='world', map_epoch='map', map_revision=1, **kwargs)


def request():
    req = PlanRoute.Request()
    for p in (req.start, req.goal):
        p.header.frame_id = 'world'
        p.pose.orientation.w = 1.0
    req.goal.pose.position.x, req.goal.pose.position.y, req.goal.pose.position.z = 1.0, 1.0, 0.55
    return req


def test_native_heights_tangent_yaw_and_path_publication(bridge):
    node, io = bridge
    observed = []
    sub = io.create_subscription(Path, '/pct_planned_path', observed.append, 10)
    wait(lambda: node._path_pub.get_subscription_count() > 0)
    client = io.create_client(PlanRoute, '/lite3_nav2/plan_route')
    assert client.wait_for_service(timeout_sec=2)
    future = client.call_async(request())
    wait(future.done)
    result = future.result()
    assert result.accepted
    assert [p.pose.position.z for p in result.path.poses] == [0.35, 0.45, 0.55]
    assert result.path.header.frame_id == 'world'
    assert result.path.header.stamp.sec > 0
    assert result.path.poses[0].pose.orientation.w == 1.0
    assert result.path.poses[1].pose.orientation.z == pytest.approx(math.sin(math.pi/4))
    assert result.path.poses[2].pose.orientation.z == pytest.approx(math.sin(math.pi/4))
    assert node._planner.calls[0][2] == dict(start_layer=None, end_layer=None, optimize=True)
    wait(lambda: observed)
    assert observed[-1] == result.path
    io.destroy_subscription(sub)


def test_goal_heading_override_and_unspecified_http_heading(bridge):
    node, _ = bridge
    req = request()
    req.goal.pose.orientation.z = math.sin(-0.3)
    req.goal.pose.orientation.w = math.cos(-0.3)
    result = node.plan_route(req, PlanRoute.Response())
    assert result.accepted and result.path.poses[-1].pose.orientation == req.goal.pose.orientation
    node.submit_goal(goal_payload())
    result = node.plan_route(req, PlanRoute.Response())
    assert result.accepted
    assert result.path.poses[-1].pose.orientation.z == pytest.approx(math.sin(math.pi/4))
    with node._lock:
        node.jobs['request']['path_heading'] = False
    req.goal.pose.orientation.z, req.goal.pose.orientation.w = 0.0, 1.0
    result = node.plan_route(req, PlanRoute.Response())
    assert result.path.poses[-1].pose.orientation.w == 1.0


def test_invalid_route_inputs_and_height_count_rejected(bridge):
    node, _ = bridge
    req = request()
    req.start.header.frame_id = 'map'
    assert not node.plan_route(req, PlanRoute.Response()).accepted
    req = request()
    req.goal.pose.position.x = float('nan')
    assert not node.plan_route(req, PlanRoute.Response()).accepted
    assert not node._planner.calls
    node._planner.heights.pop()
    assert not node.plan_route(request(), PlanRoute.Response()).accepted


def test_odometry_state_and_http_validation(bridge):
    node, io = bridge
    pub = io.create_publisher(Odometry, '/quad_0/body_pose', qos_profile_sensor_data)
    wait(lambda: pub.get_subscription_count() > 0)
    odom = Odometry()
    odom.header.frame_id, odom.header.stamp.sec, odom.header.stamp.nanosec = 'world', 12, 34
    odom.pose.pose.position.x, odom.pose.pose.position.z = 1.5, 0.35
    odom.pose.pose.orientation.z, odom.pose.pose.orientation.w = math.sin(0.2), math.cos(0.2)
    odom.twist.twist.linear.x, odom.twist.twist.angular.z = 0.12, 0.3
    pub.publish(odom)
    wait(lambda: node.measurement_body_pose is not None)
    state = http(node, '/state')
    assert state['run_id'] == 'unit' and state['run_epoch_ns'] == 42
    assert state['navigation_authority'] == 'Nav2'
    assert state['readiness']['body_pose_ready']
    body = state['measurement_body_pose']
    assert body['stamp_ns'] == 12000000034
    assert body['yaw_rad'] == pytest.approx(0.4)
    assert body['vx'] == 0.12 and body['wz'] == 0.3
    invalid = goal_payload()
    invalid['target_ground_xyz'][0] = float('nan')
    with pytest.raises(urllib.error.HTTPError) as error:
        http(node, '/goal', invalid)
    assert error.value.code == 400
    assert not node.jobs
    result = http(node, '/cancel', {'request_id': 'cancel', 'target_request_id': 'absent'})
    assert result['status'] == 'not_found'


@pytest.mark.parametrize('terminal', ['arrived', 'cancelled', 'failed'])
def test_http_nav2_action_lifecycle(bridge, terminal):
    node, io = bridge
    release = threading.Event()
    goals = []
    def execute(handle):
        goals.append(handle.request)
        end = time.monotonic() + 4.0
        while not release.is_set() and not handle.is_cancel_requested and time.monotonic() < end:
            time.sleep(0.01)
        if handle.is_cancel_requested:
            handle.canceled()
        elif terminal == 'arrived':
            handle.succeed()
        else:
            handle.abort()
        return NavigateToPose.Result()
    server = ActionServer(io, NavigateToPose, '/nav2_internal/navigate_to_pose', execute_callback=execute,
        cancel_callback=lambda _: CancelResponse.ACCEPT, callback_group=ReentrantCallbackGroup())
    node._test_action_servers.append(server)
    try:
        wait(node._client.server_is_ready)
        response = http(node, '/goal', goal_payload(target_yaw_rad=0.7))
        assert response == {'ok': True, 'request_id': 'request', 'status': 'pending'}
        wait(lambda: node.jobs['request']['status'] == 'running')
        wait(lambda: goals)
        assert goals[-1].pose.pose.position.z == pytest.approx(0.55)
        assert goals[-1].pose.pose.orientation.z == pytest.approx(math.sin(0.35))
        assert http(node, '/state')['service']['current_owner']['request_id'] == 'request'
        if terminal == 'cancelled':
            response = http(node, '/cancel', {'request_id': 'cancel', 'target_request_id': 'request'})
            assert response == {'ok': True, 'status': 'cancelling', 'target_request_id': 'request'}
        else:
            release.set()
        wait(lambda: node.terminal_results)
        state = http(node, '/state')
        result = state['terminal_results'][0]
        assert result['seq'] == 1 and result['request_id'] == 'request' and result['status'] == terminal
        assert result['monotonic_ns'] > 0
        assert state['service']['current_owner'] is None
        assert state['jobs']['request']['status'] == terminal
    finally:
        release.set()


def test_pending_cancel_and_request_id_idempotence(bridge):
    node, _ = bridge
    response = http(node, '/goal', goal_payload())
    assert response['status'] == 'pending'
    assert http(node, '/goal', goal_payload())['status'] == 'pending'
    assert len(node.jobs) == 1
    http(node, '/cancel', {'request_id': 'cancel', 'target_request_id': 'request'})
    wait(lambda: node.terminal_results)
    assert node.terminal_results[-1]['status'] == 'cancelled'
    assert len(node.terminal_results) == 1


def test_generated_profile_uses_direct_topics_and_builtin_tree(tmp_path):
    import xml.etree.ElementTree as ET
    import yaml
    from ament_index_python.packages import get_package_share_directory
    from pathlib import Path as FilePath
    from lite3_nav2_bridge.profile import write_profile
    native = FilePath(get_package_share_directory('scan_planner')) / 'config/planner.yaml'
    output = tmp_path / 'navigation.yaml'
    write_profile(output, native, False)
    config = yaml.safe_load(output.read_text())
    controller = config['controller_server']['ros__parameters']['SCAN']
    assert controller['command_topic'] == '/quad_0/cmd_vel'
    assert controller['route_topic'] == '/pct_path'
    bt = config['/nav2_internal/bt_navigator']['ros__parameters']
    tree = ET.parse(bt['default_bt_xml_filename'])
    assert tree.getroot().find('.//Sequence').attrib['name'] == 'NavigateWithDirectRoute'
    assert tree.getroot().find('.//ComputePathToPose').attrib['planner_id'] == 'PCT'
    assert tree.getroot().find('.//FollowPath').attrib['controller_id'] == 'SCAN'
    assert tree.getroot().find('.//Wait').attrib['wait_duration'] == '0.1'
    assert tree.getroot().find('.//Wait').attrib['server_name'] == '/wait'
