"""Lead-owned live ROS/C++ cancellation probe with synthetic odometry, no robot."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import time


def main():
    import rclpy
    from geometry_msgs.msg import Point
    from nav_msgs.msg import Odometry
    from scan_planner_msgs.msg import Bspline, P2BCancel, P2BAdmission, P2BStampedTwist

    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rclpy.init()
    node = rclpy.create_node('p2b_lead_controller_probe')
    commands, receipts = [], []
    odom_pub = node.create_publisher(Odometry, 'body_pose', 10)
    spline_pub = node.create_publisher(Bspline, 'planning/bspline', 10)
    cancel_pub = node.create_publisher(P2BCancel, '/p2b/scan_cancel', 10)

    def on_command(msg):
        commands.append({'wall_s': time.monotonic(), 'generation': msg.generation,
                         'command_id': msg.command_id, 'traj_id': msg.traj_id,
                         'vx': msg.twist.linear.x, 'vy': msg.twist.linear.y,
                         'wz': msg.twist.angular.z})

    def on_receipt(msg):
        receipts.append({'wall_s': time.monotonic(), 'generation': msg.generation,
                         'command_id': msg.command_id, 'status': msg.status,
                         'hold_confirmed': msg.hold_confirmed,
                         'consumer': getattr(msg, 'consumer', None)})

    node.create_subscription(P2BStampedTwist, '/quad_0/raw_scan_cmd_vel', on_command, 100)
    node.create_subscription(P2BAdmission, '/p2b/scan_admission', on_receipt, 100)
    log = (args.output / 'controller.log').open('w')
    process = subprocess.Popen(['ros2', 'run', 'scan_planner', 'closed_loop_controller',
                                '--ros-args', '-p', 'use_sim_time:=false'], stdout=log,
                               stderr=subprocess.STDOUT)
    checks = {}

    def spin(seconds):
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            if process.poll() is not None:
                raise RuntimeError('Controller exited during probe')
            odom = Odometry()
            odom.header.stamp = node.get_clock().now().to_msg()
            odom.header.frame_id = 'world'
            odom.pose.pose.orientation.w = 1.0
            odom.pose.pose.position.z = 1.91
            odom_pub.publish(odom)
            rclpy.spin_once(node, timeout_sec=0.02)

    def identity(msg, generation):
        msg.run_id = 'lead-controller-probe'
        msg.epoch = 1
        msg.request_id = 'request-' + str(generation)
        msg.goal_id = 'goal-' + str(generation)
        msg.route_id = 'route-' + str(generation)
        msg.command_id = 'command-' + str(generation)
        msg.generation = generation
        msg.map_epoch = 'map-1'
        msg.map_revision = 1
        return msg

    def spline(generation, traj_id):
        msg = identity(Bspline(), generation)
        msg.order = 3
        msg.traj_id = traj_id
        msg.start_time = node.get_clock().now().to_msg()
        msg.knots = [float(i) * 0.25 for i in range(10)]
        msg.pos_pts = [Point(x=0.2 * float(i), y=0.0, z=1.91) for i in range(6)]
        return msg

    def nonzero(rows):
        return any(math.hypot(r['vx'], r['vy']) > 0.001 or abs(r['wz']) > 0.001 for r in rows)

    try:
        spin(1.5)
        spline_pub.publish(spline(1, 1))
        begin = len(commands)
        spin(0.6)
        checks['native_controller_emits_nonzero_for_valid_spline'] = nonzero(commands[begin:])
        cancel = identity(P2BCancel(), 1)
        cancel.reason = 'lead_cancel'
        cancel_pub.publish(cancel)
        spin(0.4)
        checks['matching_controller_hold_receipt'] = any(
            r['generation'] == 1 and r['status'] == 'stopped' and r['hold_confirmed']
            and r['consumer'] == 'controller' for r in receipts)
        begin = len(commands)
        # Higher trajectory number cannot override a cancelled command generation.
        spline_pub.publish(spline(1, 100))
        spin(0.5)
        checks['late_cancelled_spline_does_not_resume'] = not nonzero(commands[begin:])
        spline_pub.publish(spline(2, 101))
        begin = len(commands)
        spin(0.5)
        checks['next_generation_can_execute'] = nonzero(commands[begin:])
        cancel_pub.publish(cancel)
        spline_pub.publish(spline(1, 999))
        begin = len(commands)
        spin(0.4)
        checks['old_cancel_and_spline_do_not_replace_new_identity'] = (
            nonzero(commands[begin:]) and all(r['generation'] == 2 for r in commands[begin:]))
        future_cancel = identity(P2BCancel(), 3)
        future_cancel.reason = 'cancel_before_spline'
        cancel_pub.publish(future_cancel)
        spin(0.2)
        # Settle generation 2, then prove earlier generation-3 cancellation persists.
        current_cancel = identity(P2BCancel(), 2)
        current_cancel.reason = 'cleanup_generation_2'
        cancel_pub.publish(current_cancel)
        spin(0.4)
        begin = len(commands)
        spline_pub.publish(spline(3, 1000))
        spin(0.4)
        checks['cancel_before_spline_tombstone'] = not nonzero(commands[begin:])
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=5)
        node.destroy_node()
        rclpy.shutdown()
        log.close()
        (args.output / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        (args.output / 'receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')
        (args.output / 'result.json').write_text(json.dumps(
            {'passed': len(checks) == 6 and all(checks.values()), 'checks': checks,
             'claim': 'Actual ROS/C++ controller boundary with synthetic odometry and splines; no simulator or robot.'}, indent=2) + '\n')
    if len(checks) != 6 or not all(checks.values()):
        raise RuntimeError('Controller identity/cancellation probe failed: ' + repr(checks))


if __name__ == '__main__':
    main()
