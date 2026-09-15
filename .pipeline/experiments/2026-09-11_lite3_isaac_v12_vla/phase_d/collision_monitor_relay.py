"""Phase D.0c relay: client <-> Nav2 collision_monitor <-> Isaac lockstep server (design Decision 8).

Transport only. Every safety decision is made by the unmodified upstream `nav2_collision_monitor` node; this process
moves data between the lockstep wire protocol and ROS 2 topics, one control tick at a time:

1. The client (VLA or scripted) sends CMD_VEL_V1 + STEP_REQUEST_V1 to this relay instead of the simulator.
2. mode `monitor`: publish `/clock` at the simulation time of the last reply, publish the last LiDAR cloud (the
   simulator's SENSOR_FRAME_V1, transformed into `base_link`) stamped with its own simulation time, then publish the
   command as TwistStamped on `cmd_vel_in` and wait for the node's `cmd_vel_out` carrying the same stamp. If none arrives
   within `--reply-timeout-s` wall seconds, the tick is sent as a stop (0, 0, 0). mode `passthrough`: forward unchanged
   (the control condition; it proves the relay itself changes nothing).
3. Forward the (possibly filtered) command to the simulator with the client's own sequence number and timestamp, so the
   bridge's freshness checks and 250 ms watchdog see exactly what the client sent.
4. Forward STATUS_V1, BODY_STATE_V2 and IMAGE_FRAME_V1 back unchanged; keep SENSOR_FRAME_V1 for the next tick.

Simulation time is offset by `--time-offset-s` on the ROS side, because ROS treats time 0 as "unset".
Fault injection for the stale-source test: `--drop-cloud-after-sim-s` stops publishing clouds after that time.
Runs inside the task's RoboStack Jazzy prefix (Python 3.12, rclpy).
"""

import argparse
import json
import socket
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'phase_c'))
import lockstep_protocol as lp                                          # noqa: E402

import rclpy                                                            # noqa: E402
from builtin_interfaces.msg import Time                                 # noqa: E402
from geometry_msgs.msg import TwistStamped                              # noqa: E402
from lifecycle_msgs.msg import Transition                               # noqa: E402
from lifecycle_msgs.srv import ChangeState, GetState                    # noqa: E402
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy, qos_profile_sensor_data  # noqa
from rosgraph_msgs.msg import Clock                                     # noqa: E402
from sensor_msgs.msg import PointCloud2, PointField                     # noqa: E402

try:
    from nav2_msgs.msg import CollisionMonitorState
except ImportError:  # the state topic is diagnostic only
    CollisionMonitorState = None

ACTION_NAMES = {0: 'DO_NOTHING', 1: 'STOP', 2: 'SLOWDOWN', 3: 'APPROACH', 4: 'LIMIT'}


def ros_time(sim_ns, offset_ns):
    total = int(sim_ns) + offset_ns
    return Time(sec=total // 1_000_000_000, nanosec=total % 1_000_000_000)


def rotate(q_xyzw, v):
    """Rotate vector v by unit quaternion q (x, y, z, w)."""
    x, y, z, w = q_xyzw
    tx, ty, tz = 2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0])
    return (v[0] + w * tx + (y * tz - z * ty), v[1] + w * ty + (z * tx - x * tz), v[2] + w * tz + (x * ty - y * tx))


def conjugate(q_xyzw):
    return (-q_xyzw[0], -q_xyzw[1], -q_xyzw[2], q_xyzw[3])


def cloud_in_base(sensor):
    """SENSOR_FRAME_V1 points (sensor frame) -> base frame, using the body and sensor world poses it carries."""
    points = lp.unpack_xyz_points(sensor.point_count, sensor.points_xyz_f32_be)
    body_inv = conjugate(sensor.body_quaternion_xyzw)
    offset = rotate(body_inv, tuple(s - b for s, b in zip(sensor.sensor_position, sensor.body_position)))
    out = []
    for p in points:
        world_rel = rotate(sensor.sensor_quaternion_xyzw, p)          # sensor frame -> world orientation
        base = rotate(body_inv, world_rel)                              # world orientation -> base orientation
        out.append((base[0] + offset[0], base[1] + offset[1], base[2] + offset[2]))
    return out


def min_leg_clearance(points, args):
    """Diagnostic only (the node decides): smallest 2D distance from a cloud point inside the height band to the D.0a
    leg-width rectangle in base_link, negative inside it. None if no point is in the band."""
    x0, x1, half_y = args.leg_rect_x_min, args.leg_rect_x_max, args.leg_rect_half_y
    best = None
    for x, y, z in points:
        if not args.band_min_z <= z <= args.band_max_z:
            continue
        dx, dy = max(x0 - x, 0.0, x - x1), max(-half_y - y, 0.0, y - half_y)
        d = (dx * dx + dy * dy) ** 0.5 if dx or dy else -min(x - x0, x1 - x, y + half_y, half_y - y)
        best = d if best is None else min(best, d)
    return None if best is None else round(best, 4)


def make_cloud(points, stamp, frame_id):
    import struct
    msg = PointCloud2()
    msg.header.stamp = stamp
    msg.header.frame_id = frame_id
    msg.height, msg.width = 1, len(points)
    msg.fields = [PointField(name=n, offset=4 * i, datatype=PointField.FLOAT32, count=1) for i, n in enumerate('xyz')]
    msg.is_bigendian, msg.point_step, msg.row_step, msg.is_dense = False, 12, 12 * len(points), True
    msg.data = b''.join(struct.pack('<fff', *p) for p in points)
    return msg


class Relay:
    def __init__(self, args):
        self.args = args
        self.offset_ns = int(args.time_offset_s * 1e9)
        rclpy.init()
        self.node = rclpy.create_node('lockstep_collision_relay')
        reliable = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST)
        self.clock_pub = self.node.create_publisher(Clock, '/clock', QoSProfile(
            depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.cloud_pub = self.node.create_publisher(PointCloud2, args.cloud_topic, qos_profile_sensor_data)
        self.cmd_pub = self.node.create_publisher(TwistStamped, args.cmd_in_topic, reliable)
        self.replies = {}
        self.node.create_subscription(TwistStamped, args.cmd_out_topic, self.on_cmd_out, reliable)
        self.last_state = None
        self.last_published_cloud_sim_ns = None
        if CollisionMonitorState is not None:
            self.node.create_subscription(CollisionMonitorState, args.state_topic, self.on_state, reliable)

    def on_cmd_out(self, msg):
        key = (msg.header.stamp.sec, msg.header.stamp.nanosec)
        self.replies[key] = (msg.twist.linear.x, msg.twist.linear.y, msg.twist.angular.z)

    def on_state(self, msg):
        self.last_state = {'action': ACTION_NAMES.get(msg.action_type, msg.action_type), 'polygon': msg.polygon_name}

    def lifecycle(self, name):
        change = self.node.create_client(ChangeState, '/{}/change_state'.format(name))
        get = self.node.create_client(GetState, '/{}/get_state'.format(name))
        deadline = time.time() + self.args.lifecycle_timeout_s
        for client in (change, get):
            while not client.wait_for_service(timeout_sec=1.0):
                if time.time() > deadline:
                    raise RuntimeError('lifecycle services of {} not available'.format(name))
        for transition in (Transition.TRANSITION_CONFIGURE, Transition.TRANSITION_ACTIVATE):
            future = change.call_async(ChangeState.Request(transition=Transition(id=transition)))
            rclpy.spin_until_future_complete(self.node, future, timeout_sec=self.args.lifecycle_timeout_s)
            if not future.done() or not future.result().success:
                raise RuntimeError('lifecycle transition {} failed for {}'.format(transition, name))
        future = get.call_async(GetState.Request())
        rclpy.spin_until_future_complete(self.node, future, timeout_sec=10.0)
        return future.result().current_state.label if future.done() else None

    def filter(self, command, sim_ns, sensor, sensor_sim_ns):
        """Returns ((vx, vy, wz), record) for one tick through the monitor."""
        stamp = ros_time(sim_ns, self.offset_ns)
        self.clock_pub.publish(Clock(clock=stamp))
        published_points = None
        drop = self.args.drop_cloud_after_sim_s
        if sensor is not None and not (drop is not None and sim_ns >= drop * 1e9):
            points = cloud_in_base(sensor)
            self.cloud_pub.publish(make_cloud(points, ros_time(sensor_sim_ns, self.offset_ns), self.args.base_frame))
            published_points = points
            self.last_published_cloud_sim_ns = sensor_sim_ns
        # Give the node a moment to take /clock (its own clock thread) and the cloud before the command arrives.
        end = time.time() + self.args.settle_wall_s
        while time.time() < end:
            rclpy.spin_once(self.node, timeout_sec=max(0.0, end - time.time()))
        msg = TwistStamped()
        msg.header.stamp = stamp
        msg.header.frame_id = self.args.base_frame
        msg.twist.linear.x, msg.twist.linear.y, msg.twist.angular.z = command.vx, command.vy, command.wz
        key = (stamp.sec, stamp.nanosec)
        self.replies.pop(key, None)
        started = time.time()
        self.cmd_pub.publish(msg)
        while key not in self.replies and time.time() - started < self.args.reply_timeout_s:
            rclpy.spin_once(self.node, timeout_sec=0.01)
        wait_ms = (time.time() - started) * 1e3
        reply = self.replies.pop(key, None)
        filtered = reply if reply is not None else (0.0, 0.0, 0.0)
        last = self.last_published_cloud_sim_ns
        # `cloud_*` describe what the node was given; `state_last_received` is the node's latest state message, which it
        # publishes only on change and may deliver after cmd_vel_out, so attribute actions from in/out, not from it.
        return filtered, {'monitor_reply': reply is not None, 'monitor_wait_ms': round(wait_ms, 1),
                          'cloud_published': published_points is not None,
                          'cloud_points_published': len(published_points) if published_points is not None else 0,
                          'cloud_min_leg_clearance_m': (min_leg_clearance(published_points, self.args)
                                                        if published_points is not None else None),
                          'last_published_cloud_age_ms': (sim_ns - last) / 1e6 if last is not None else None,
                          'state_last_received': self.last_state}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--listen-port', type=int, required=True)
    parser.add_argument('--server-port', type=int, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--mode', choices=('monitor', 'passthrough'), required=True)
    parser.add_argument('--monitor-node', default='collision_monitor')
    parser.add_argument('--cmd-in-topic', default='/cmd_vel_in')
    parser.add_argument('--cmd-out-topic', default='/cmd_vel_out')
    parser.add_argument('--state-topic', default='/collision_monitor_state')
    parser.add_argument('--cloud-topic', default='/lidar/points')
    parser.add_argument('--base-frame', default='base_link')
    parser.add_argument('--time-offset-s', type=float, default=1000.0)
    parser.add_argument('--settle-wall-s', type=float, default=0.03)
    parser.add_argument('--reply-timeout-s', type=float, default=2.0)
    parser.add_argument('--lifecycle-timeout-s', type=float, default=60.0)
    parser.add_argument('--drop-cloud-after-sim-s', type=float)
    parser.add_argument('--expect-cloud', action='store_true',
                        help='the simulator appends SENSOR_FRAME_V1 to every reply (server --lidar-cloud)')
    # Diagnostic clearance only; the same height band as collision_monitor_lite3.yaml and the D.0a leg-width rectangle.
    parser.add_argument('--band-min-z', type=float, default=-0.22)
    parser.add_argument('--band-max-z', type=float, default=0.45)
    parser.add_argument('--leg-rect-x-min', type=float, default=-0.269)
    parser.add_argument('--leg-rect-x-max', type=float, default=0.279)
    parser.add_argument('--leg-rect-half-y', type=float, default=0.182)
    parser.add_argument('--accept-timeout-s', type=float, default=1800.0)
    parser.add_argument('--server-connect-timeout-s', type=float, default=1200.0)
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == 'monitor' and not args.expect_cloud:
        parser.error('monitor mode needs --expect-cloud: the collision monitor has no other obstacle source')
    relay = Relay(args) if args.mode == 'monitor' else None
    record = {'mode': args.mode, 'args': {k: str(v) for k, v in vars(args).items()}}
    if relay is not None:
        record['monitor_state_after_activation'] = relay.lifecycle(args.monitor_node)

    # Listen first so the client can queue its connection; then wait for the simulator (Isaac starts slowly).
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(('127.0.0.1', args.listen_port))
    listener.listen(1)
    listener.settimeout(args.accept_timeout_s)
    (args.output_dir / 'RELAY_LISTENING').write_text('{}\n'.format(args.listen_port))
    print('RELAY_LISTENING port={} mode={}'.format(args.listen_port, args.mode), flush=True)
    deadline = time.time() + args.server_connect_timeout_s
    while True:
        try:
            server = socket.create_connection(('127.0.0.1', args.server_port), timeout=5.0)
            break
        except OSError:
            if time.time() > deadline:
                raise
            time.sleep(1.0)
    server.settimeout(900.0)
    server.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    client, _ = listener.accept()
    client.settimeout(900.0)
    client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def forward(sock, frame):
        lp.send_frame(sock, lp.encode_frame(frame.header.message_type, frame.header.sequence,
                                            frame.header.timestamp_ns, frame.payload))

    log = open(args.output_dir / 'relay_ticks.jsonl', 'w')
    sim_ns, sensor, sensor_sim_ns = 0, None, 0
    ticks = changed = changed_after_tick0 = no_reply = 0
    first_changed_tick, cloud_counts = None, []
    end_reason = None
    try:
        while True:
            try:
                command_frame = lp.recv_frame(client)
                request_frame = lp.recv_frame(client)
            except (EOFError, ConnectionError, socket.timeout) as error:
                end_reason = 'client_closed: {!r}'.format(error)
                break
            command = lp.decode_command_payload(command_frame.payload)
            request = lp.decode_step_request_payload(request_frame.payload)
            entry = {'tick': ticks, 'sim_ns': sim_ns, 'in': [command.vx, command.vy, command.wz]}
            if relay is not None:
                filtered, info = relay.filter(command, sim_ns, sensor, sensor_sim_ns)
                entry.update(info)
                no_reply += 0 if info['monitor_reply'] else 1
            else:
                filtered = (command.vx, command.vy, command.wz)
            entry['out'] = list(filtered)
            if any(abs(a - b) > 1e-9 for a, b in zip(filtered, (command.vx, command.vy, command.wz))):
                # Tick 0 always stops in monitor mode: no cloud exists before the first reply (pointcloud.cpp).
                changed += 1
                changed_after_tick0 += 1 if ticks > 0 else 0
                first_changed_tick = ticks if first_changed_tick is None else first_changed_tick
            lp.send_frame(server, lp.encode_frame(
                lp.MessageType.CMD_VEL_V1, command_frame.header.sequence, command_frame.header.timestamp_ns,
                lp.encode_command_payload(lp.CommandV1(*filtered))))
            forward(server, request_frame)
            status_frame = lp.recv_frame(server)
            body_frame = lp.recv_frame(server)
            status = lp.decode_status_payload(status_frame.payload)
            body = lp.decode_body_state_v2_payload(body_frame.payload)
            forward(client, status_frame)
            forward(client, body_frame)
            terminated = status.termination_code != 0
            if request.want_image and not terminated:
                forward(client, lp.recv_frame(server))
            sim_ns = body.simulation_time_ns
            if args.expect_cloud and not terminated:
                sensor_frame = lp.recv_frame(server)
                if sensor_frame.header.message_type != lp.MessageType.SENSOR_FRAME_V1:
                    raise lp.ProtocolError('expected SENSOR_FRAME_V1 from the simulator')
                sensor, sensor_sim_ns = lp.decode_sensor_payload(sensor_frame.payload), sim_ns
                entry['cloud_points_received'] = sensor.point_count
                cloud_counts.append(sensor.point_count)
            entry['termination_code'] = status.termination_code
            log.write(json.dumps(entry) + '\n')
            ticks += 1
            if terminated:
                end_reason = 'simulator_terminated code={}'.format(status.termination_code)
                break
    except BaseException as error:
        end_reason = 'relay_error: {!r}'.format(error)
        raise
    finally:
        log.close()
        for sock in (client, server, listener):
            try:
                sock.close()
            except OSError:
                pass
        record.update({'ticks': ticks, 'commands_changed_by_monitor': changed,
                       'commands_changed_after_tick0': changed_after_tick0, 'first_changed_tick': first_changed_tick,
                       'monitor_no_reply_ticks': no_reply, 'clouds_received': len(cloud_counts),
                       'first_cloud_points': cloud_counts[0] if cloud_counts else None,
                       'min_cloud_points': min(cloud_counts) if cloud_counts else None,
                       'end_reason': end_reason, 'final_sim_s': sim_ns / 1e9})
        (args.output_dir / 'relay_episode.json').write_text(json.dumps(record, indent=2) + '\n')
        print('RELAY_DONE ticks={} changed={} no_reply={} end={}'.format(ticks, changed, no_reply, end_reason),
              flush=True)
        if relay is not None:
            relay.node.destroy_node()
            rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
