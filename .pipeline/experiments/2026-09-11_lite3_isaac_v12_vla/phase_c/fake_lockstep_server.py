"""Test double for isaac_lockstep_server.py: same wire protocol and command path, a unicycle instead of Isaac.

Commands pass through the pinned bridge's real `LatestCommandState` on the simulated clock, so the clamp, the sequence
and freshness checks and the 250 ms watchdog are the production code. The robot is a first-order unicycle
(tau 0.15 s on v and w), and the image is synthetic. It exists to test the client, the protocol and the
controllers without a GPU; it says nothing about locomotion.

Phase D.0c options, both off by default: `--lidar-cloud` appends a SENSOR_FRAME_V1 to every reply, with points sampled on
the landmark boxes' vertical faces and filtered by the pinned adapter's `world_hits_to_sensor_points` (no occlusion);
`--footprint-contact` ends the episode when the URDF leg-width footprint (scripts/phase_d0_footprint_clearance.py)
overlaps a box, instead of the crude centre-distance test.
"""

import argparse
import json
import math
import socket
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lockstep_protocol as lp                                      # noqa: E402
from lockstep_common import TERMINATION_CODES, horizontal_distance, landmark, load_episode  # noqa: E402

POLICY_DT_NS = 20_000_000
TAU_S = 0.15


def episode_landmarks(path):
    return load_episode(path)['landmarks']


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--episode', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--bridge-source', type=Path, required=True, help='lite3_sim_bridge source root')
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--client-timeout-s', type=float, default=60.0)
    parser.add_argument('--lidar-cloud', action='store_true')
    parser.add_argument('--footprint-contact', action='store_true')
    args = parser.parse_args(argv)
    sys.path.insert(0, str(args.bridge_source))
    from lite3_sim_bridge.command_state import CommandLimits, LatestCommandState
    from lite3_sim_bridge.isaac_adapter_core import world_hits_to_sensor_points
    import importlib.util
    spec = importlib.util.spec_from_file_location('footprint', HERE.parent / 'scripts' / 'phase_d0_footprint_clearance.py')
    footprint = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(footprint)
    legs = footprint.rectangle(*footprint.FOOTPRINTS['legs'])
    boxes = [footprint.rectangle(i['center'][0] - i['size'][0] / 2, i['center'][0] + i['size'][0] / 2,
                                 i['center'][1] - i['size'][1] / 2, i['center'][1] + i['size'][1] / 2)
             for i in episode_landmarks(args.episode)]
    face_points = []
    for item in episode_landmarks(args.episode):
        (cx, cy), (sx, sy) = item['center'][:2], item['size'][:2]
        corners = [(cx - sx / 2, cy - sy / 2), (cx + sx / 2, cy - sy / 2), (cx + sx / 2, cy + sy / 2), (cx - sx / 2, cy + sy / 2)]
        for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]):
            n = max(1, int(round(math.hypot(bx - ax, by - ay) / 0.05)))
            for k in range(n):
                for z in (0.1, 0.3, 0.5, 0.7):
                    face_points.append((ax + (bx - ax) * k / n, ay + (by - ay) * k / n, z))
    sensor_offset = (0.182399336, 0.0, 0.108541081)   # the adapter's default --sensor-translation on TORSO
    min_clearance = math.inf

    episode = load_episode(args.episode)
    target = landmark(episode, episode['target_landmark'])
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    state = LatestCommandState(CommandLimits(0.75, 0.35, 1.0), timeout_ns=250_000_000)
    x = y = yaw = v = w = 0.0
    sim_ns, step, requests, images, sequence = 0, 0, 0, 0, 0
    epoch = time.time_ns()
    width, height = int(episode['camera']['width']), int(episode['camera']['height'])
    fx = (width / 2) / math.tan(math.radians(float(episode['camera']['hfov']) / 2))
    max_sim_ns = int(float(episode['max_sim_seconds']) * 1e9)

    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', args.port))
    server.listen(1)
    (out / 'LISTENING').write_text('{}\n'.format(args.port))
    connection, _ = server.accept()
    connection.settimeout(args.client_timeout_s)
    log = open(out / 'fake_steps.jsonl', 'w')
    termination = None

    def send(message_type, payload):
        nonlocal sequence
        sequence += 1
        lp.send_frame(connection, lp.encode_frame(message_type, sequence, sim_ns, payload))

    while True:
        try:
            command_frame = lp.recv_frame(connection)
            request_frame = lp.recv_frame(connection)
        except (EOFError, ConnectionError, socket.timeout):
            termination = 'client_lost'
            break
        requests += 1
        command = lp.decode_command_payload(command_frame.payload)
        request = lp.decode_step_request_payload(request_frame.payload)
        try:
            state.update(command, command_frame.header.sequence, command_frame.header.timestamp_ns, sim_ns)
        except Exception as error:  # noqa: BLE001
            termination = 'command_rejected'
            log.write(json.dumps({'rejected': repr(error)}) + '\n')
        for _ in range(0 if termination else request.duration_ns // POLICY_DT_NS):
            snapshot = state.snapshot(sim_ns)
            applied = snapshot.command
            alpha = (POLICY_DT_NS / 1e9) / TAU_S
            v += alpha * (applied.vx - v)
            w += alpha * (applied.wz - w)
            yaw += w * POLICY_DT_NS / 1e9
            x += v * math.cos(yaw) * POLICY_DT_NS / 1e9
            y += v * math.sin(yaw) * POLICY_DT_NS / 1e9
            sim_ns += POLICY_DT_NS
            step += 1
            log.write(json.dumps({'step': step, 'sim_ns': sim_ns, 'received': [command.vx, command.wz],
                                  'applied': [applied.vx, applied.wz], 'stale': snapshot.stale,
                                  'reason': snapshot.reason, 'watchdog_events': snapshot.watchdog_events,
                                  'xy': [x, y], 'yaw': yaw}) + '\n')
            if args.footprint_contact:
                placed = footprint.place(legs, x, y, yaw)
                clearance = min(footprint.signed_distance(placed, box)[0] for box in boxes)
                min_clearance = min(min_clearance, clearance)
                if clearance <= 0.0:
                    termination = 'nonfoot_contact'
            else:
                for item in episode['landmarks']:
                    if (abs(x - item['center'][0]) < item['size'][0] / 2 + 0.3
                            and abs(y - item['center'][1]) < item['size'][1] / 2 + 0.2):
                        termination = 'nonfoot_contact'
            if termination is None and sim_ns >= max_sim_ns:
                termination = 'max_sim_time'
            if termination:
                break
        if termination is None and request.end_episode:
            termination = 'client_end'
        snapshot = state.snapshot(sim_ns)
        send(lp.MessageType.STATUS_V1, lp.encode_status_payload(lp.StatusV1(
            200.0, 50.0, 0.0, 0.0, 4, 0, snapshot.watchdog_events,
            int(lp.StatusFlag.TERMINATED) if termination else 0,
            TERMINATION_CODES[termination] if termination else 0)))
        half = yaw / 2
        send(lp.MessageType.BODY_STATE_V2, lp.encode_body_state_v2_payload(lp.BodyStateV2(
            (x, y, 0.31), (0.0, 0.0, math.sin(half), math.cos(half)), (v * math.cos(yaw), v * math.sin(yaw), 0.0),
            (0.0, 0.0, w), (v, 0.0, 0.0), (0.0, 0.0, w), sim_ns, requests, epoch)))
        if request.want_image and termination is None:
            images += 1
            rgb = np.zeros((height, width, 3), dtype=np.uint8)
            rgb[: height // 2] = (90, 140, 220)
            rgb[height // 2:] = (170, 170, 170)
            depth = np.full((height, width), 2.0, dtype='<f4')
            send(lp.MessageType.IMAGE_FRAME_V1, lp.encode_image_frame_payload(lp.ImageFrameV1(
                images, sim_ns, width, height, (fx, fx, width / 2, height / 2),
                (x + 0.27 * math.cos(yaw), y + 0.27 * math.sin(yaw), 0.40), (0.0, 0.0, math.sin(half), math.cos(half)),
                rgb.tobytes(), depth.tobytes())))
        if args.lidar_cloud and termination is None:
            sensor_xyz = (x + sensor_offset[0] * math.cos(yaw), y + sensor_offset[0] * math.sin(yaw),
                          0.31 + sensor_offset[2])
            sensor_wxyz = (math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2))
            points = world_hits_to_sensor_points(face_points, sensor_xyz, sensor_wxyz, 0.10, 12.0, minimum_world_z=0.05)
            count, data = lp.pack_xyz_points(points)
            send(lp.MessageType.SENSOR_FRAME_V1, lp.encode_sensor_payload(lp.SensorFrameV1(
                (x, y, 0.31), (0.0, 0.0, math.sin(half), math.cos(half)), sensor_xyz,
                (0.0, 0.0, sensor_wxyz[3], sensor_wxyz[0]), bytes(32), count, data)))
        if termination:
            break
    log.close()
    (out / 'fake_episode.json').write_text(json.dumps({
        'termination': termination, 'sim_seconds': sim_ns / 1e9, 'requests': requests, 'images': images,
        'final_xy': [x, y], 'final_distance_to_target_m': horizontal_distance((x, y), target['center']),
        'watchdog_events': state.snapshot(sim_ns).watchdog_events,
        'min_leg_footprint_clearance_m': min_clearance if args.footprint_contact else None}, indent=2) + '\n')
    connection.close()
    server.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
