"""Local, GPU-free tests of the Phase C loop: protocol, lockstep timing, upstream controllers, clamp and watchdog.

    python test_lockstep_local.py --bridge-source <lite3_sim_bridge source> --controllers-dir <InternNav scripts/realworld>

Needs numpy, scipy, pillow and casadi 3.7.2 (the version installed for the rented 4090, setup/phase_c_pydeps.json).
"""

import argparse
import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lockstep_protocol as lp  # noqa: E402

EPISODE = HERE / 'episodes' / 'c_red_box_ahead_v1.json'


def free_port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def start_fake(args, out):
    port = free_port()
    process = subprocess.Popen([sys.executable, str(HERE / 'fake_lockstep_server.py'), '--episode', str(EPISODE),
                                '--output-dir', str(out), '--bridge-source', str(args.bridge_source),
                                '--port', str(port)])
    for _ in range(100):
        if (out / 'LISTENING').exists():
            return process, port
        time.sleep(0.05)
    process.kill()
    raise RuntimeError('fake server did not start')


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def raw_step(sock, sequence, timestamp_ns, v, w, duration_ns, end=False):
    lp.send_frame(sock, lp.encode_frame(lp.MessageType.CMD_VEL_V1, sequence, timestamp_ns,
                                        lp.encode_command_payload(lp.CommandV1(v, 0.0, w))))
    lp.send_frame(sock, lp.encode_frame(lp.MessageType.STEP_REQUEST_V1, sequence, timestamp_ns,
                                        lp.encode_step_request_payload(lp.StepRequestV1(duration_ns, sequence, False,
                                                                                         end))))
    status = lp.decode_status_payload(lp.recv_frame(sock).payload)
    body = lp.decode_body_state_v2_payload(lp.recv_frame(sock).payload)
    return status, body


def test_scripted_episode(args, root):
    out = root / 'episode'
    server, port = start_fake(args, out / 'sim')
    client = subprocess.run([sys.executable, str(HERE / 'vla_lockstep_client.py'), '--episode', str(EPISODE),
                             '--output-dir', str(out / 'client'), '--port', str(port), '--agent', 'scripted',
                             '--script', 'look_down,straight,straight,straight,left,straight,stop',
                             '--controllers-dir', str(args.controllers_dir)], capture_output=True, text=True,
                            timeout=300)
    server.wait(timeout=30)
    assert client.returncode == 0, client.stderr[-3000:]
    episode = json.loads((out / 'client' / 'client_episode.json').read_text())
    decisions = read_jsonl(out / 'client' / 'decisions.jsonl')
    ticks = read_jsonl(out / 'client' / 'ticks.jsonl')
    steps = read_jsonl(out / 'sim' / 'fake_steps.jsonl')
    sim = json.loads((out / 'sim' / 'fake_episode.json').read_text())

    assert episode['termination'] == 'client_end', episode['termination']
    assert episode['stopped_by_model'] and len(decisions) == 7, (episode['stopped_by_model'], len(decisions))
    assert decisions[0]['looked_down'] and decisions[0]['first_action'] == [5] and 'trajectory' in decisions[0]
    # System 2 is counted by call, not inferred: the look-down decision is two System 2 calls, every decision >= 1.
    assert decisions[0]['s2_calls'] == 2 and all(d['s2_calls'] >= 1 for d in decisions), [d['s2_calls'] for d in decisions]
    # Milliseconds of scripted latency round up to one tick before the plan applies; the next image follows upstream's
    # 0.3 s planning period.
    assert all(d['apply_ticks'] == 1 and d['ticks'] == 3 for d in decisions), [(d['apply_ticks'], d['ticks'])
                                                                              for d in decisions]
    assert ticks[0]['mode'] is None and ticks[1]['mode'] == 'mpc' and decisions[4]['mode_after'] == 'pid'
    assert decisions[-1]['discrete_action'] == [0]
    # The trajectory was moved into the world with the odometry captured with its image, first three points skipped.
    assert len(decisions[1]['trajectory_world']) == 30
    assert 'error' in decisions[0]['trajectory_tovw']
    # Commands every 100 ms simulated: the 250 ms watchdog never fires and nothing is stale once commanding started.
    assert sim['watchdog_events'] == 0 and all(not s['stale'] for s in steps), sim['watchdog_events']
    assert sim['final_xy'][0] > 0.3, sim['final_xy']
    # After STOP the PD hold keeps the base still: last second of steps moves < 5 cm.
    tail = [s['xy'] for s in steps[-50:]]
    assert abs(tail[-1][0] - tail[0][0]) < 0.05 and abs(tail[-1][1] - tail[0][1]) < 0.05, (tail[0], tail[-1])
    max_v = max(abs(t['v']) for t in ticks)
    assert max_v <= 0.6 + 1e-6, max_v   # upstream MPC v_max 0.4, PID max_v 0.6
    return {'decisions': len(decisions), 'ticks': len(ticks), 'final_xy': sim['final_xy'], 'max_v': max_v,
            'modes': sorted({str(t['mode']) for t in ticks})}


def test_latency_faithful_timing(args, root):
    """A 0.27 s decision: the old plan runs 0.3 s (ceil), the new plan 0.1 s, next image 0.4 s after the last."""
    out = root / 'latency'
    server, port = start_fake(args, out / 'sim')
    client = subprocess.run([sys.executable, str(HERE / 'vla_lockstep_client.py'), '--episode', str(EPISODE),
                             '--output-dir', str(out / 'client'), '--port', str(port), '--agent', 'scripted',
                             '--script', 'straight,straight,stop', '--scripted-latency-s', '0.27',
                             '--controllers-dir', str(args.controllers_dir)], capture_output=True, text=True,
                            timeout=300)
    server.wait(timeout=30)
    assert client.returncode == 0, client.stderr[-3000:]
    decisions = read_jsonl(out / 'client' / 'decisions.jsonl')
    ticks = read_jsonl(out / 'client' / 'ticks.jsonl')
    assert all(d['apply_ticks'] == 3 and d['ticks'] == 4 for d in decisions), [(d['apply_ticks'], d['ticks'])
                                                                              for d in decisions]
    assert [t['mode'] for t in ticks[:4]] == [None, None, None, 'mpc'], [t['mode'] for t in ticks[:4]]
    for d in decisions[:-1]:
        assert d['applied_at_sim_ns'] - d['image_sim_ns'] == 300_000_000, d
        assert d['next_image_sim_ns'] - d['image_sim_ns'] == 400_000_000, d
    assert all(abs(a['image_sim_ns'] - b['next_image_sim_ns']) == 0 for a, b in zip(decisions[1:], decisions[:-1]))
    return {'apply_ticks': decisions[0]['apply_ticks'], 'ticks': decisions[0]['ticks'],
            'latency_s': round(decisions[0]['latency_s'], 3)}


def test_watchdog_and_clamp(args, root):
    out = root / 'watchdog'
    server, port = start_fake(args, out)
    with socket.create_connection(('127.0.0.1', port)) as sock:
        raw_step(sock, 1, 0, 2.0, 0.0, 500_000_000)   # clamp to 0.75, then hold 0.5 s without a new command
        raw_step(sock, 2, 500_000_000, 0.0, 0.0, 0, end=True)
    server.wait(timeout=30)
    steps = read_jsonl(out / 'fake_steps.jsonl')
    early, late = steps[5], steps[-1]
    assert abs(early['applied'][0] - 0.75) < 1e-9 and not early['stale'], early
    assert late['stale'] and late['reason'] == 'watchdog_timeout' and late['applied'][0] == 0.0, late
    first_stale = next(s for s in steps if s['stale'])
    assert 250_000_000 < first_stale['sim_ns'] <= 290_000_000, first_stale['sim_ns']
    return {'clamped_vx': early['applied'][0], 'watchdog_trip_sim_ns': first_stale['sim_ns']}


def test_stale_command_rejected(args, root):
    out = root / 'stale'
    server, port = start_fake(args, out)
    with socket.create_connection(('127.0.0.1', port)) as sock:
        raw_step(sock, 1, 0, 0.3, 0.0, 400_000_000)
        status, _ = raw_step(sock, 2, 0, 0.3, 0.0, 100_000_000)   # stamped with a sim time 400 ms old
    server.wait(timeout=30)
    assert status.termination_code == 8, status   # command_rejected
    return {'termination_code': status.termination_code}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bridge-source', type=Path, required=True)
    parser.add_argument('--controllers-dir', type=Path, required=True)
    parser.add_argument('--keep', type=Path, help='write test outputs here instead of a temp dir')
    args = parser.parse_args()
    root = args.keep or Path(tempfile.mkdtemp(prefix='phase_c_test_'))
    results = {}
    for test in (test_scripted_episode, test_latency_faithful_timing, test_watchdog_and_clamp,
                 test_stale_command_rejected):
        results[test.__name__] = test(args, root)
        print('PASS', test.__name__, results[test.__name__], flush=True)
    print('ALL PASS; outputs in', root)


if __name__ == '__main__':
    main()
