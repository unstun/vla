"""Bounded polling summaries and once-per-plan, lossless run evidence."""
from collections import deque
import json
from pathlib import Path
import threading


class PlanHistory:
    def __init__(self, path=None, identity=None):
        self.path = None if path is None else Path(path)
        self.identity = dict(identity or {})
        self.records = deque(maxlen=50)
        self.summaries = deque(maxlen=50)
        self.sequence = 0
        self.error = None
        self.lock = threading.Lock()
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # A run owns one new artifact; never append to a previous run.
            with self.path.open('x', encoding='utf-8'):
                pass

    def append(self, record):
        # Called only by PCT planning workers, never heartbeat/odometry callbacks.
        with self.lock:
            self.sequence += 1
            record = dict(record, history_seq=self.sequence)
            summary = {key: value for key, value in record.items()
                       if key not in ('request', 'waypoints_m')}
            summary['waypoint_count'] = len(record.get('waypoints_m', ()))
            self.records.append(record)
            self.summaries.append(summary)
            if self.path is not None:
                try:
                    row = dict(record, evidence_identity=self.identity)
                    with self.path.open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n')
                except OSError as error:
                    # Diagnostics must not turn a successful route into a planner
                    # failure, but evidence failure is explicit and latched.
                    self.error = str(error)

    def snapshot(self, include_history=False):
        with self.lock:
            return {'plan_history': list(self.records if include_history else self.summaries),
                    'history_detail': 'full' if include_history else 'summary',
                    'plan_count': self.sequence,
                    'history_evidence': {'path': None if self.path is None else str(self.path),
                                         'configured': self.path is not None,
                                         'error': self.error}}
