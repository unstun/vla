"""Actual Foxy Nav2 servers with a labelled flat kinematic sensor/plant fixture.

This is not Newton physics, a quadruped policy, localization qualification, or a
hardware test. The plant integrates received Twist and publishes measured pose.
"""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import signal
import time

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped, TransformStamped, Twist
from lifecycle_msgs.srv import ChangeState
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import OccupancyGrid, Odometry
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from sensor_msgs.msg import LaserScan
from tf2_msgs.msg import TFMessage


class FlatPlant(Node):
    def __init__(self):
        super().__init__('nav2_flat_kinematic_fixture')
        self.x = self.y = self.yaw = 0.0
        self.command = Twist()
        self.command_time = 0.0
        self.last_tick = time.monotonic()
        self.commands = []
        self.samples = []
        self.tf = self.create_publisher(TFMessage, '/tf', 10)
        self.odom = self.create_publisher(Odometry, '/odom', 10)
        self.scan = self.create_publisher(LaserScan, '/scan', 10)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                         reliability=ReliabilityPolicy.RELIABLE)
        self.map = self.create_publisher(OccupancyGrid, '/map', qos)
        self.create_subscription(Twist, '/cmd_vel', self.on_command, 10)
        self.create_timer(0.02, self.tick)
        self.create_timer(0.1, self.sensors)
        self.action = ActionClient(self, NavigateToPose, '/navigate_to_pose')
        grid = OccupancyGrid()
        grid.header.frame_id = 'world'
        grid.header.stamp = self.get_clock().now().to_msg()
        grid.info.resolution = 0.1
        grid.info.width = grid.info.height = 100
        grid.info.origin.position.x = grid.info.origin.position.y = -5.0
        grid.info.origin.orientation.w = 1.0
        grid.data = [0] * 10000
        self.map.publish(grid)

    def on_command(self, msg):
        self.command = msg
        self.command_time = time.monotonic()
        self.commands.append([self.command_time, msg.linear.x, msg.linear.y, msg.angular.z])

    def tick(self):
        now = time.monotonic()
        dt = min(now - self.last_tick, 0.1)
        self.last_tick = now
        cmd = self.command if now - self.command_time < 0.3 else Twist()
        self.x += dt * (math.cos(self.yaw) * cmd.linear.x - math.sin(self.yaw) * cmd.linear.y)
        self.y += dt * (math.sin(self.yaw) * cmd.linear.x + math.cos(self.yaw) * cmd.linear.y)
        self.yaw += dt * cmd.angular.z
        stamp = self.get_clock().now().to_msg()
        tf = TransformStamped()
        tf.header.frame_id = 'world'
        tf.header.stamp = stamp
        tf.child_frame_id = 'base_link'
        tf.transform.translation.x = self.x
        tf.transform.translation.y = self.y
        tf.transform.rotation.z = math.sin(self.yaw / 2)
        tf.transform.rotation.w = math.cos(self.yaw / 2)
        self.tf.publish(TFMessage(transforms=[tf]))
        odom = Odometry()
        odom.header = tf.header
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation = tf.transform.rotation
        odom.twist.twist = cmd
        self.odom.publish(odom)
        self.samples.append([now, self.x, self.y, self.yaw])

    def sensors(self):
        scan = LaserScan()
        scan.header.frame_id = 'base_link'
        scan.header.stamp = self.get_clock().now().to_msg()
        scan.angle_min = -math.pi
        scan.angle_max = math.pi
        scan.angle_increment = 2 * math.pi / 360
        scan.range_min = 0.05
        scan.range_max = 8.0
        scan.scan_time = 0.1
        scan.ranges = [float('inf')] * 361
        self.scan.publish(scan)

    def wait(self, predicate, timeout=10.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.01)
            if predicate():
                return
        raise TimeoutError('Nav2 fixture wait expired')

    def pause(self, seconds):
        end = time.monotonic() + seconds
        self.wait(lambda: time.monotonic() >= end, seconds + 1)

    def transition(self, name, transition):
        client = self.create_client(ChangeState, '/' + name + '/change_state')
        self.wait(client.service_is_ready, 20)
        request = ChangeState.Request()
        request.transition.id = transition
        future = client.call_async(request)
        self.wait(future.done, 30)
        assert future.result().success, (name, transition)
        self.destroy_client(client)

    def goal(self, x, y=0.0):
        request = NavigateToPose.Goal()
        request.pose = PoseStamped()
        request.pose.header.frame_id = 'world'
        request.pose.header.stamp = self.get_clock().now().to_msg()
        request.pose.pose.position.x = float(x)
        request.pose.pose.position.y = float(y)
        request.pose.pose.orientation.w = 1.0
        future = self.action.send_goal_async(request)
        self.wait(future.done)
        handle = future.result()
        assert handle.accepted
        return handle


def profile(output):
    share = Path(get_package_share_directory('nav2_bringup'))
    candidates = list(share.rglob('nav2_params.yaml'))
    if len(candidates) != 1:
        raise RuntimeError('Expected one installed Foxy upstream profile')
    original = candidates[0].read_text()
    (output / 'upstream_nav2_params.yaml').write_text(original)
    data = yaml.safe_load(original)
    def clocks(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == 'use_sim_time': obj[k] = False
                else: clocks(v)
    clocks(data)
    bt = data['bt_navigator']['ros__parameters']
    bt.update(global_frame='world', robot_base_frame='base_link', odom_topic='/odom',
              default_bt_xml_filename=str(output / 'stock_tree.xml'))
    controller = data['controller_server']['ros__parameters']
    controller['controller_frequency'] = 20.0
    controller['FollowPath'].update(max_vel_x=0.5, max_speed_xy=0.5)
    for key in ('local_costmap', 'global_costmap'):
        p = data[key][key]['ros__parameters']
        p.update(global_frame='world', robot_base_frame='base_link', robot_radius=0.22,
                 update_frequency=10.0, publish_frequency=2.0,
                 plugins=['static_layer', 'obstacle_layer', 'inflation_layer'])
        p['static_layer'] = {'plugin': 'nav2_costmap_2d::StaticLayer',
                             'map_subscribe_transient_local': True, 'map_topic': '/map'}
        p['obstacle_layer'] = {'plugin': 'nav2_costmap_2d::ObstacleLayer',
            'observation_sources': 'scan', 'scan': {'topic': '/scan', 'data_type': 'LaserScan',
            'clearing': True, 'marking': True, 'inf_is_valid': True,
            'observation_persistence': 0.0, 'expected_update_rate': 0.2}}
    config = output / 'stock.yaml'
    config.write_text(yaml.safe_dump(data))
    (output / 'stock_tree.xml').write_text('''<root main_tree_to_execute="MainTree">
 <BehaviorTree ID="MainTree"><PipelineSequence>
  <RateController hz="1.0"><ComputePathToPose goal="{goal}" path="{path}" planner_id="GridBased"/></RateController>
  <FollowPath path="{path}" controller_id="FollowPath"/>
 </PipelineSequence></BehaviorTree></root>\n''')
    return config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    config = profile(args.output)
    rclpy.init()
    plant = FlatPlant()
    processes, logs = [], []
    report = {'scope': 'stock Foxy Nav2 with flat kinematic fixture; no Newton/robot', 'passed': False}
    try:
        for package, executable in [('nav2_controller', 'controller_server'),
                                     ('nav2_planner', 'planner_server'),
                                     ('nav2_bt_navigator', 'bt_navigator')]:
            log = (args.output / (executable + '.log')).open('w')
            logs.append(log)
            processes.append(subprocess.Popen(['ros2', 'run', package, executable, '--ros-args',
                '-r', '__node:=' + executable, '--params-file', str(config)], stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True))
        for name in ('controller_server', 'planner_server', 'bt_navigator'):
            plant.transition(name, 1)
            plant.transition(name, 3)
        plant.wait(lambda: plant.action.server_is_ready(), 10)
        handle = plant.goal(2.0)
        result = handle.get_result_async()
        plant.wait(result.done, 40)
        report['goal_status'] = result.result().status
        report['goal_error_m'] = math.hypot(plant.x - 2.0, plant.y)
        assert report['goal_status'] == 4 and report['goal_error_m'] <= 0.30, report
        handle = plant.goal(4.0)
        start = plant.x
        plant.wait(lambda: plant.x > start + 0.15, 10)
        cancel = handle.cancel_goal_async()
        plant.wait(cancel.done)
        result = handle.get_result_async()
        plant.wait(result.done)
        plant.pause(0.4)
        stopped = (plant.x, plant.y)
        plant.pause(0.8)
        report['cancel_status'] = result.result().status
        report['post_cancel_motion_m'] = math.hypot(plant.x - stopped[0], plant.y - stopped[1])
        report['command_count'] = len(plant.commands)
        report['last_command'] = plant.commands[-1][1:]
        assert report['cancel_status'] == 5
        assert report['post_cancel_motion_m'] < 1e-5
        assert report['last_command'] == [0.0, 0.0, 0.0]
        report['passed'] = True
    except Exception as exc:
        report['error'] = repr(exc)
        raise
    finally:
        (args.output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
        (args.output / 'samples.json').write_text(json.dumps(plant.samples))
        (args.output / 'commands.json').write_text(json.dumps(plant.commands))
        for p in processes:
            if p.poll() is None: os.killpg(p.pid, signal.SIGTERM)
        for p in processes:
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired: os.killpg(p.pid, signal.SIGKILL); p.wait()
        for log in logs: log.close()
        plant.action.destroy()
        plant.destroy_node()
        rclpy.shutdown()
    print(json.dumps(report))


if __name__ == '__main__':
    main()
