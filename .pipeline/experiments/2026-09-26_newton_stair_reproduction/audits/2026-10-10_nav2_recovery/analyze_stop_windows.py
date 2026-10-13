"""Replay original applied-state stop rules; bound unknown gateway callback timing."""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
TASK = Path('/data/sun/vla_mppi_20261009')
sys.path.insert(0, str(BASE / 'versions/v127'))
sys.path.insert(0, str(BASE / 'runtime_sources/backend_adapter'))
from analyze_remote import Capture
from backend_adapter.applied_evidence import AppliedCommandSnapshot, StopEvidenceConfig, StopEvidenceWindow, FRESH_STOP_REASONS


def analyze(tag):
    capture = Capture(TASK / 'trials' / tag / 'runs' / tag)
    observations = capture.rows('artifacts/reactive_observations.jsonl')
    sent = capture.rows('applied_sent.jsonl')
    epoch = capture.json('episode_request.json')['run_epoch_ns']
    config = capture.json('backend_config.json')['applied_evidence']
    cfg = StopEvidenceConfig(**{k: config[k] for k in ('stop_command_norm', 'stop_speed_mps',
                                                     'stop_yaw_rate_radps', 'stop_dwell_sim_seconds')})
    samples = []
    for row in sent:
        payload = row['snapshot']
        raw = json.dumps(payload, separators=(',', ':'), allow_nan=False).encode()
        assert hashlib.sha256(raw).hexdigest() == row['sha256'] == row['ack']['sha256']
        sample = AppliedCommandSnapshot.from_mapping(payload)
        assert sample.run_id == tag and sample.run_epoch_ns == epoch
        assert row['ack']['ok'] and row['ack']['sequence'] == sample.state_sequence
        # This timestamp follows atomic storage and the original reader check.
        samples.append((row['ack']['linux_receive_ns'], sample))
    events = []
    seen = set()
    for row in observations:
        if row['event'] != 'scan_cancel' or row['data']['generation'] in seen:
            continue
        generation = row['data']['generation']
        seen.add(generation)
        start = row['wall_monotonic_ns']
        next_route = next((x['wall_monotonic_ns'] for x in observations
                           if x['event'] == 'pct_route' and x['data']['generation'] > generation
                           and x['wall_monotonic_ns'] > start), samples[-1][0] + 1)
        cases = []
        # Recorder receipt is not the gateway reset timestamp. Bracket it rather
        # than pretending that the original callback schedule was captured.
        for offset_ms in (-20, 0, 20):
            reset = start + offset_ms * 1000000
            window = StopEvidenceWindow(cfg)
            window.reset(reset)
            first = None
            longest = 0.0
            reasons = collections.Counter()
            for received, sample in samples:
                if received < reset or received >= next_route:
                    continue
                checks = {
                    'command_precedes_reset': sample.command_source_timestamp_ns < reset,
                    'command_stale': sample.command_stale,
                    'command_reason': sample.command_reason not in FRESH_STOP_REASONS,
                    'nonzero_translation': sample.applied_xy_norm() > cfg.stop_command_norm,
                    'nonzero_rotation': abs(sample.applied_command[2]) > cfg.stop_command_norm,
                    'body_speed': sample.horizontal_speed_mps > cfg.stop_speed_mps,
                    'body_yaw_rate': abs(sample.yaw_rate_radps) > cfg.stop_yaw_rate_radps,
                }
                reasons.update(k for k, failed in checks.items() if failed)
                accepted = window.observe(sample, tag, epoch)
                if window.first_ok_sim_time_s is not None and window.last_ok_sim_time_s is not None:
                    longest = max(longest, window.last_ok_sim_time_s - window.first_ok_sim_time_s)
                if accepted and first is None:
                    first = {'after_cancel_wall_s': (received - start) / 1e9,
                             'sim_time_s': sample.sim_time_s, 'state_sequence': sample.state_sequence}
            cases.append({'reset_offset_ms': offset_ms, 'first_possible_complete_window': first,
                          'longest_contiguous_stop_sim_s': longest, 'failed_predicate_samples': dict(reasons)})
        events.append({'generation': generation, 'reason': row['data']['reason'],
                       'cancel_clock_ns': row['clock_ns'], 'cancel_receipt_monotonic_ns': start,
                       'end_before_next_route_or_capture_s': (next_route - start) / 1e9,
                       'window_replays': cases})
    return {'run': tag, 'events': events, 'source': capture.sources,
            'limits': ['Every applied sample is replayed; gateway polling may have consumed fewer.',
                       'Recorder receipt brackets gateway reset only approximately; plus/minus20ms is a sensitivity check.',
                       'Controller hold acknowledgement and fresh ROS odometry are separate required gates.',
                       'An available complete window is necessary evidence, not proof the gateway consumed it.']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    report = {'runs': [analyze(tag) for tag in args.run],
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'original_stop_rule_sha256': hashlib.sha256((BASE / 'runtime_sources/backend_adapter/backend_adapter/applied_evidence.py').read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'runs': len(report['runs']), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
