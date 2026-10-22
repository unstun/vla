"""Exercise only stock Wait's lifecycle and one-second action; no navigation goal."""
import os
import subprocess
import time
from pathlib import Path
import rclpy
from rclpy.action import ActionClient
from lifecycle_msgs.srv import ChangeState
from nav2_msgs.action import Wait
from ament_index_python.packages import get_package_prefix


def test_stock_wait_activates_and_keeps_robot_command_topic_unowned(tmp_path):
    rclpy.init()
    node=rclpy.create_node('wait_component_check')
    executable=Path(get_package_prefix('nav2_recoveries'))/'lib/nav2_recoveries/recoveries_server'
    log=(tmp_path/'wait.log').open('w')
    process=subprocess.Popen([str(executable),'--ros-args','--params-file',os.environ['TERRAIN_TEST_PROFILE']],
        stdout=log,stderr=subprocess.STDOUT)
    def complete(future):
        rclpy.spin_until_future_complete(node,future,timeout_sec=4.)
        assert future.done(), (tmp_path/'wait.log').read_text()
        return future.result()
    try:
        client=node.create_client(ChangeState,'/recoveries_server/change_state')
        assert client.wait_for_service(timeout_sec=5.), (tmp_path/'wait.log').read_text()
        for transition in (1,3):
            request=ChangeState.Request();request.transition.id=transition
            assert complete(client.call_async(request)).success, (tmp_path/'wait.log').read_text()
        action=ActionClient(node,Wait,'/wait');assert action.wait_for_server(timeout_sec=3.)
        goal=Wait.Goal();goal.time.sec=1
        started=time.monotonic();handle=complete(action.send_goal_async(goal));assert handle.accepted
        assert complete(handle.get_result_async()).status==4
        assert 0.9 <= time.monotonic()-started < 3.
        assert not node.get_publishers_info_by_topic('/quad_0/cmd_vel')
        for transition in (4,2):
            request=ChangeState.Request();request.transition.id=transition
            assert complete(client.call_async(request)).success
        action.destroy()
    finally:
        process.terminate()
        try: process.wait(timeout=3.)
        except subprocess.TimeoutExpired: process.kill();process.wait(timeout=3.)
        log.close();node.destroy_node();rclpy.shutdown()
