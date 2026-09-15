"""Phase D.0c test driver: commands the lockstep simulator without any model, one 0.1 s tick per request.

    python3 scripted_command_client.py --port P --output-dir DIR replay --ticks RUN/client/ticks.jsonl
    python3 scripted_command_client.py --port P --output-dir DIR straight --v 0.3 --seconds 20
    python3 scripted_command_client.py --port P --output-dir DIR line --y-line 0.45 --v 0.3 --seconds 25

`replay` resends the (v, w) of a Phase C client log tick by tick. The simulator is deterministic for identical
commands (RESULT_PHASE_C.md, "Variance"), so a replay reproduces that episode's motion until something, such as the
collision monitor, changes a command. `straight` holds a constant speed. `line` steers onto the line y = Y heading +x
with a proportional heading law (a test trajectory, not a planner). The wire contract is the Phase C client's: CMD_VEL_V1
stamped with the last received simulation time, then STEP_REQUEST_V1; replies STATUS_V1 and BODY_STATE_V2. Standard
library only.
"""

import argparse
import json
import math
import socket
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'phase_c'))
import lockstep_protocol as lp                                          # noqa: E402
from lockstep_common import CONTROL_TICK_NS, TERMINATION_CODES          # noqa: E402

TERMINATION_NAMES = {code: name for name, code in TERMINATION_CODES.items()}


class Link:
    def __init__(self, port, timeout_s):
        deadline = time.time() + timeout_s
        while True:
            try:
                self.sock = socket.create_connection(('127.0.0.1', port), timeout=5.0)
                break
            except OSError:
                if time.time() > deadline:
                    raise
                time.sleep(1.0)
        self.sock.settimeout(600.0)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sequence = 0
        self.sim_ns = 0

    def step(self, v, w, end_episode=False):
        self.sequence += 1
        lp.send_frame(self.sock, lp.encode_frame(lp.MessageType.CMD_VEL_V1, self.sequence, self.sim_ns,
                                                 lp.encode_command_payload(lp.CommandV1(v, 0.0, w))))
        lp.send_frame(self.sock, lp.encode_frame(lp.MessageType.STEP_REQUEST_V1, self.sequence, self.sim_ns,
                                                 lp.encode_step_request_payload(lp.StepRequestV1(
                                                     CONTROL_TICK_NS, self.sequence, False, end_episode))))
        status_frame = lp.recv_frame(self.sock)
        body_frame = lp.recv_frame(self.sock)
        if (status_frame.header.message_type != lp.MessageType.STATUS_V1
                or body_frame.header.message_type != lp.MessageType.BODY_STATE_V2):
            raise lp.ProtocolError('expected STATUS_V1 then BODY_STATE_V2')
        status = lp.decode_status_payload(status_frame.payload)
        body = lp.decode_body_state_v2_payload(body_frame.payload)
        if body.simulation_time_ns < self.sim_ns:
            raise lp.ProtocolError('simulation time went backwards')
        self.sim_ns = body.simulation_time_ns
        return status, body


def yaw_of(body):
    qx, qy, qz, qw = body.orientation_world_xyzw
    return math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))


def schedule(args):
    if args.mode == 'replay':
        rows = [json.loads(line) for line in Path(args.ticks).read_text().splitlines() if line.strip()]
        commands = [(float(r['v']), float(r['w'])) for r in rows]
        limit = len(commands) if args.max_ticks is None else min(len(commands), args.max_ticks)
        return lambda tick, body: commands[tick] if tick < limit else None
    ticks = int(round(args.seconds * 1e9 / CONTROL_TICK_NS))
    if args.mode == 'straight':
        return lambda tick, body: (args.v, 0.0) if tick < ticks else None

    def line(tick, body):
        if tick >= ticks:
            return None
        if body is None:
            return (0.0, 0.0)
        y_error = body.position_world[1] - args.y_line
        heading = math.atan2(-y_error, args.lookahead)
        error = math.atan2(math.sin(heading - yaw_of(body)), math.cos(heading - yaw_of(body)))
        return (args.v, max(-args.w_max, min(args.w_max, args.k_heading * error)))
    return line


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--connect-timeout-s', type=float, default=1200.0)
    sub = parser.add_subparsers(dest='mode', required=True)
    replay = sub.add_parser('replay')
    replay.add_argument('--ticks', type=Path, required=True)
    replay.add_argument('--max-ticks', type=int)
    straight = sub.add_parser('straight')
    straight.add_argument('--v', type=float, required=True)
    straight.add_argument('--seconds', type=float, required=True)
    line = sub.add_parser('line')
    line.add_argument('--y-line', type=float, required=True)
    line.add_argument('--v', type=float, default=0.3)
    line.add_argument('--seconds', type=float, required=True)
    line.add_argument('--lookahead', type=float, default=1.0)
    line.add_argument('--k-heading', type=float, default=1.5)
    line.add_argument('--w-max', type=float, default=0.5)
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    command_for = schedule(args)
    link = Link(args.port, args.connect_timeout_s)
    log = open(args.output_dir / 'scripted_ticks.jsonl', 'w')
    termination, body, tick = None, None, 0
    started = time.time()
    try:
        while True:
            command = command_for(tick, body)
            end = command is None
            v, w = (0.0, 0.0) if end else command
            status, body = link.step(v, w, end_episode=end)
            log.write(json.dumps({'tick': tick, 'sim_ns': body.simulation_time_ns, 'v': v, 'w': w,
                                  'xy': list(body.position_world[:2]), 'yaw': yaw_of(body),
                                  'termination_code': status.termination_code}) + '\n')
            tick += 1
            if status.termination_code:
                termination = TERMINATION_NAMES.get(status.termination_code, str(status.termination_code))
                break
    except (OSError, EOFError, lp.ProtocolError) as error:
        termination = 'link_error: {!r}'.format(error)
    log.close()
    record = {'mode': args.mode, 'args': {k: str(v) for k, v in vars(args).items()}, 'termination': termination,
              'ticks_sent': tick, 'sim_seconds': link.sim_ns / 1e9, 'wall_seconds': time.time() - started,
              'final_xy': list(body.position_world[:2]) if body else None}
    (args.output_dir / 'scripted_episode.json').write_text(json.dumps(record, indent=2) + '\n')
    print('SCRIPTED_DONE termination={} ticks={} sim_s={:.1f}'.format(termination, tick, link.sim_ns / 1e9), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
