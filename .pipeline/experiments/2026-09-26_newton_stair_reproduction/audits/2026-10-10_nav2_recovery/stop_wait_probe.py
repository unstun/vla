"""Exercise the installed gateway wait loop with recorded applied-stop evidence."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import hashlib
import json
import threading

from lite3_nav2_bridge import gateway
from backend_adapter.applied_evidence import AppliedCommandSnapshot, StopEvidenceConfig, StopEvidenceWindow
from std_srvs.srv import Trigger


def run_case(data, mode):
    clock = SimpleNamespace(now=data['cancel_receipt_monotonic_ns'] / 1e9)
    samples = [(r['ack']['linux_receive_ns'] / 1e9,
                AppliedCommandSnapshot.from_mapping(r['snapshot'])) for r in data['samples']]
    cfg = StopEvidenceConfig(**data['config'])

    class Fixture:
        lock = threading.RLock()
        closing = False
        released = False
        binding = True
        ready = None
        stopping = True
        gate = SimpleNamespace(owner=True, cancel_pending=True, hold_ack=True)
        index = 0
        stop_verified_at = 0.0

        def begin_stop(self, reason):
            self.window = StopEvidenceWindow(cfg)
            self.window.reset(data['cancel_receipt_monotonic_ns'])

        def stopped(self):
            while self.index < len(samples) and samples[self.index][0] <= clock.now:
                available, sample = samples[self.index]
                self.index += 1
                if self.window.observe(sample, data['run'], data['epoch']) and mode != 'never_proved':
                    self.stop_verified_at = available
            return gateway.MissionGateway.stopped(self)

        def release(self):
            assert self.stopped()
            gateway.MissionGateway.release(self)
            self.released = True

    fixture = Fixture()
    start = clock.now

    def sleep(seconds):
        clock.now += seconds
        if mode == 'closing' and clock.now - start >= 2:
            fixture.closing = True

    original_time = gateway.time
    gateway.time = SimpleNamespace(monotonic=lambda: clock.now, sleep=sleep)
    try:
        response = gateway.MissionGateway.wait_stopped(fixture, None, Trigger.Response())
    finally:
        gateway.time = original_time
    return {'mode': mode, 'success': response.success, 'released': fixture.released,
            'elapsed_s': clock.now - start, 'message': response.message}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    for row in data['samples']:
        raw = json.dumps(row['snapshot'], separators=(',', ':'), allow_nan=False).encode()
        assert hashlib.sha256(raw).hexdigest() == row['sha256'] == row['ack']['sha256']
    result = {'cases': [run_case(data, mode) for mode in ('recorded_stop', 'never_proved', 'closing')],
              'input_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest(),
              'gateway_source_sha256': hashlib.sha256(Path(gateway.__file__).read_bytes()).hexdigest(),
              'scope': 'Actual installed gateway wait loop plus original StopEvidenceWindow and recorded samples; deterministic clock, pre-established hold acknowledgement, no DDS or physics claim.'}
    assert not result['cases'][1]['success'] and not result['cases'][1]['released']
    assert not result['cases'][2]['success'] and not result['cases'][2]['released']
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
