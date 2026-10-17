"""Loopback HTTP/ROS task-adapter checks; no planner is loaded by this process."""
import copy
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
from nav2_msgs.action import NavigateToPose
from lite3_nav2_interfaces.srv import RouteSession
from nav_msgs.msg import Odometry, Path
from rclpy.action import ActionServer, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import qos_profile_sensor_data

from lite3_nav2_bridge.mission_bridge import MissionBridge


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
    node = MissionBridge()
    io = rclpy.create_node('mission_test_io')
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    executor.add_node(io)
    node._test_sessions = []
    def session(request, response):
        node._test_sessions.append(request)
        if hasattr(node, "_test_session_hook"):
            node._test_session_hook(request)
        response.accepted = True
        return response
    io.create_service(RouteSession, '/lite3_nav2/route_session', session)
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


def test_task_adapter_has_no_planner_service_or_route_cache(bridge):
    node, _ = bridge
    assert not hasattr(node, '_planner')
    assert not hasattr(node, '_planner_lock')
    assert not hasattr(node, '_plan_service')
    assert not hasattr(node, '_path_pub')
    assert '/lite3_nav2/plan_route' not in dict(node.get_service_names_and_types())
    http(node, '/goal', goal_payload())
    job = http(node, '/state')['jobs']['request']
    assert job['target_body_xyz'] == pytest.approx([1., 1., .55])
    assert not any(key in job for key in ('cached_path', 'canonical_goal_pose', 'retained_count'))


@pytest.mark.parametrize('terminal', ['arrived', 'cancelled', 'failed'])
@pytest.mark.parametrize('yaw', [None, 0.0, 0.7])
def test_http_nav2_action_lifecycle(bridge, terminal, yaw):
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
        response = http(node, '/goal', goal_payload(**({} if yaw is None else {'target_yaw_rad': yaw})))
        assert response == {'ok': True, 'request_id': 'request', 'status': 'pending'}
        wait(lambda: node.jobs['request']['status'] == 'running')
        wait(lambda: goals)
        begin = next(req for req in node._test_sessions if req.operation == RouteSession.Request.BEGIN)
        assert begin.infer_heading == (yaw is None)
        assert begin.session_id == 'unit/42/request'
        assert begin.goal == goals[-1].pose
        assert goals[-1].pose.pose.position.z == pytest.approx(0.55)
        assert goals[-1].pose.pose.position.x == 1.0
        assert goals[-1].pose.pose.position.y == 1.0
        assert goals[-1].pose.pose.orientation.z == pytest.approx(math.sin((yaw or 0.) / 2))
        assert goals[-1].pose.pose.orientation.w == pytest.approx(math.cos((yaw or 0.) / 2))
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
        wait(lambda: any(req.operation == RouteSession.Request.END and req.session_id == begin.session_id
                         for req in node._test_sessions))
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
    import os
    bundle = FilePath(os.environ['TERRAIN_TEST_MANIFEST'])
    write_profile(output, native, False, terrain_manifest=bundle)
    config = yaml.safe_load(output.read_text())
    controller = config['controller_server']['ros__parameters']['SCAN']
    assert 'command_topic' not in controller
    assert controller['route_topic'] == '/pct_path'
    pct = config['planner_server']['ros__parameters']['PCT']
    assert pct['map_bundle'] == str(bundle.parent / 'route.pct')
    assert pct['reference_height'] == .35
    assert 'service' not in pct
    bt = config['/nav2_internal/bt_navigator']['ros__parameters']
    tree = ET.parse(bt['default_bt_xml_filename'])
    assert tree.getroot().find('.//PipelineSequence').attrib['name'] == 'NavigateWithReplanning'
    assert tree.getroot().find('.//ComputePathToPose').attrib['planner_id'] == 'PCT'
    assert tree.getroot().find('.//FollowPathWithFailure').attrib['controller_id'] == 'SCAN'
    assert tree.getroot().find('.//Wait').get('wait_duration') == '1'
    assert tree.getroot().find('.//RecoveryNode').get('number_of_retries') == '6'
    assert tree.getroot().find('.//MeasuredProgressRecovery') is None



def test_navigation_launch_assigns_command_topic_to_server(tmp_path):
    import importlib.util
    from pathlib import Path as FilePath
    from launch import LaunchContext
    from ament_index_python.packages import get_package_share_directory
    launch_file = FilePath(get_package_share_directory('lite3_nav2_bridge')) / 'launch/navigation.launch.py'
    spec = importlib.util.spec_from_file_location('navigation_launch', launch_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    import os
    terrain_manifest = os.environ['TERRAIN_TEST_MANIFEST']
    (tmp_path / 'backend.json').write_text(json.dumps({'run_id':'unit','run_epoch_ns':42,'map': {'nominal_body_height_m': .3}}))
    context = LaunchContext()
    context.launch_configurations.update({
        'use_sim_time': 'false', 'base_frame': 'base', 'odom_topic': '/quad_0/body_pose',
        'generated_params': str(tmp_path / 'params.yaml'), 'terrain_manifest': terrain_manifest,
        'backend_config': str(tmp_path / 'backend.json'),
        'native_planner_config': str(FilePath(get_package_share_directory('scan_planner')) / 'config/planner.yaml')})
    with patch.object(module, 'Node', side_effect=lambda **kwargs: kwargs), \
         patch.object(module, 'OnProcessExit', side_effect=lambda **kwargs: kwargs), \
         patch.object(module, 'RegisterEventHandler', side_effect=lambda action: {'monitor':action}):
        launched = module.nodes(context)
    server = next(node for node in launched if node.get('package') == 'nav2_controller')
    assert server['remappings'] == [('cmd_vel', '/quad_0/cmd_vel')]


def test_replanning_tree_contract():
    from pathlib import Path as FilePath
    import xml.etree.ElementTree as ET
    root = ET.parse(FilePath(__file__).parents[1] / 'config/navigate.xml').getroot()
    recovery = root.find('.//RecoveryNode')
    assert recovery.get('number_of_retries') == '6'
    pipeline = root.find('.//PipelineSequence')
    assert pipeline.get('name') == 'NavigateWithReplanning'
    assert pipeline.find('RateController') is None
    rate = pipeline.find('PlanOnGoalChange')
    assert rate.attrib == {'goal': '{goal}', 'reference': '{path}'}
    assert rate.find('ComputePathToPose').attrib == dict(goal='{goal}', path='{path}',
        planner_id='PCT', server_name='/compute_path_to_pose', server_timeout='1000')
    assert pipeline.find('FollowPathWithFailure').get('controller_id') == 'SCAN'
    assert root.find('.//Wait').get('wait_duration') == '1'
    assert root.find('.//RetryAllowed') is not None



@pytest.mark.parametrize('replace', [False, True])
def test_cancel_or_replace_during_session_ack_never_dispatches_old_goal(bridge, replace):
    node, io = bridge
    entered, release = threading.Event(), threading.Event()
    def delay(request):
        if request.operation == RouteSession.Request.BEGIN and request.session_id.endswith('/old'):
            entered.set()
            assert release.wait(3.)
    node._test_session_hook = delay
    goals = []
    def execute(handle):
        goals.append(handle.request)
        handle.succeed()
        return NavigateToPose.Result()
    server = ActionServer(io, NavigateToPose, '/nav2_internal/navigate_to_pose', execute_callback=execute,
                          callback_group=ReentrantCallbackGroup())
    node._test_action_servers.append(server)
    try:
        wait(node._client.server_is_ready)
        http(node, '/goal', goal_payload('old'))
        assert entered.wait(2.)
        if replace:
            http(node, '/goal', goal_payload('new', target_yaw_rad=0.7))
        else:
            http(node, '/cancel', {'request_id':'cancel', 'target_request_id':'old'})
        release.set()
        wait(lambda: node.jobs['old']['status'] == 'cancelled')
        if replace:
            wait(lambda: node.jobs['new']['status'] == 'arrived')
            assert len(goals) == 1
            assert goals[0].pose.pose.orientation.z == pytest.approx(math.sin(.35))
        else:
            assert not goals
        wait(lambda: any(req.operation == RouteSession.Request.END and req.session_id.endswith('/old')
                         for req in node._test_sessions))
    finally:
        release.set()


def test_critical_subprocess_abort_closes_matching_failed_finish_with_live_launch_parent(bridge,tmp_path):
    import subprocess,sys,signal
    from lite3_nav2_bridge.runtime_failure import read_json, finish_failed
    node,io=bridge
    root=tmp_path/'unit';root.mkdir();fault=root/'native_process_failure.json'
    node._failure_path=str(fault)
    node.submit_goal(goal_payload('aborted-route'))
    # Keep dispatch pending while exercising a real ROS launch child and its exit event.
    child_code="""
import resource,sys
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
from launch import LaunchService,LaunchDescription
from launch.actions import ExecuteProcess,RegisterEventHandler
from launch.event_handlers import OnProcessExit
from lite3_nav2_bridge.runtime_failure import critical_exit_handler
crash=ExecuteProcess(cmd=[sys.executable,'-c','import os,time; time.sleep(.1); os.abort()'])
keeper=ExecuteProcess(cmd=[sys.executable,'-c','import time;time.sleep(30)'])
monitor=RegisterEventHandler(OnProcessExit(target_action=crash,on_exit=critical_exit_handler(sys.argv[1],'unit',42,'controller_server')))
service=LaunchService();service.include_launch_description(LaunchDescription([monitor,keeper,crash]));service.run()
"""
    log=(tmp_path/'launch_abort.log').open('w')
    process=subprocess.Popen([sys.executable,'-c',child_code,str(fault)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        wait(lambda: read_json(fault),seconds=8.)
        assert process.poll() is None # launch parent survives the controller child
        record=read_json(fault);assert record['exit_code']==-6
        wait(lambda: node.jobs['aborted-route']['status']=='failed')
        state=node.get_state();assert state['service']['current_owner'] is None
        assert len(state['terminal_results'])==1
        terminal=state['terminal_results'][0]
        assert terminal['cause']=='native_process_exit'
        assert terminal['data']['component']=='controller_server'
        closed=finish_failed(root,{'run_epoch_ns':42},record,state)
        assert closed['backend_terminal_status']=='FAILED' and closed['observed_run_epoch_ns']==42
        assert closed['request_id']=='aborted-route' and 'exit_code=-6' in closed['note']
        assert read_json(root/'artifacts/external_episode/finish_request.json')==closed
        assert finish_failed(root,{'run_epoch_ns':42},record,state)==closed
        assert finish_failed(root,{'run_epoch_ns':43},record,state) is None
        with pytest.raises(ValueError):node.submit_goal(goal_payload('new-after-crash'))
    finally:
        oskill=__import__('os').killpg
        oskill(process.pid,signal.SIGTERM)
        process.wait(timeout=5);log.close()


def test_old_epoch_failure_ignored_and_late_acceptance_cannot_revive_failed_job(bridge,tmp_path):
    from concurrent.futures import Future
    from unittest.mock import Mock
    from lite3_nav2_bridge.runtime_failure import process_failure
    node,_=bridge;fault=tmp_path/'failure.json';node._failure_path=str(fault)
    node.submit_goal(goal_payload('late'))
    process_failure(fault,'unit',41,'controller_server',-6)
    node._check_native_health();assert node.jobs['late']['status']=='pending'
    fault.unlink();process_failure(fault,'unit',42,'controller_server',-6)
    with patch.object(node,'_end_session',side_effect=RuntimeError('session server dead')):
        node._check_native_health()
    assert node.jobs['late']['status']=='failed';assert len(node.terminal_results)==1
    assert node.terminal_results[0]['data']['session_cleanup_error']=='session server dead'
    handle=Mock();handle.accepted=True;future=Future();future.set_result(handle)
    node._accepted('late',future)
    handle.cancel_goal_async.assert_called_once()
    assert node.jobs['late']['status']=='failed' and len(node.terminal_results)==1
    node._check_native_health();assert len(node.terminal_results)==1


def test_lost_critical_node_uses_steady_timeout_and_normal_shutdown_is_ignored(bridge,tmp_path):
    from unittest.mock import Mock
    from lite3_nav2_bridge.runtime_failure import read_json,critical_exit_handler
    node,_=bridge;fault=tmp_path/'lost.json';node._failure_path=str(fault)
    node.submit_goal(goal_payload('lost'));node.jobs['lost']['status']='running'
    node._critical_timeout=.01
    client=Mock();client.service_is_ready.return_value=False
    node._liveness_clients={'/controller_server':client}
    with node._lock:
        node._health_last['/controller_server']=time.monotonic()-.02
        node._check_native_health()
    wait(lambda:node.jobs['lost']['status']=='failed')
    assert read_json(fault)['cause']=='native_node_unresponsive'
    assert node.terminal_results[-1]['cause']=='native_node_unresponsive'
    normal=tmp_path/'normal.json'
    critical_exit_handler(normal,'unit',42,'controller_server')(Mock(returncode=0),Mock(is_shutdown=True))
    assert not normal.exists()


def test_real_launch_intentional_shutdown_does_not_create_process_failure(tmp_path):
    import subprocess,sys
    fault=tmp_path/'intentional_shutdown.json'
    code="""
import sys
from launch import LaunchService,LaunchDescription
from launch.actions import ExecuteProcess,RegisterEventHandler,TimerAction,EmitEvent
from launch.events import Shutdown
from launch.event_handlers import OnProcessExit
from lite3_nav2_bridge.runtime_failure import critical_exit_handler
child=ExecuteProcess(cmd=[sys.executable,'-c','import time;time.sleep(30)'])
monitor=RegisterEventHandler(OnProcessExit(target_action=child,on_exit=critical_exit_handler(sys.argv[1],'unit',42,'controller_server')))
stop=TimerAction(period=.2,actions=[EmitEvent(event=Shutdown(reason='intentional unit-test shutdown'))])
service=LaunchService();service.include_launch_description(LaunchDescription([monitor,child,stop]));service.run()
"""
    result=subprocess.run([sys.executable,'-c',code,str(fault)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=8,text=True)
    assert result.returncode==0,result.stdout
    assert not fault.exists(),result.stdout
