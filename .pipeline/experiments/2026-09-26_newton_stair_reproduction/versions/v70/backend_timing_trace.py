"""v70 observation-only spans; never change original control or JSON results."""
from collections import deque
from contextlib import contextmanager
import gc
import json
from pathlib import Path
import threading
import time

REAL_DUMPS = json.dumps
IDENTITY = ('run_id','epoch','request_id','goal_id','route_id','command_id',
            'generation','map_epoch','map_revision')


class Trace:
    def __init__(self):
        self.rows = deque(maxlen=100000)
        self.finished = threading.Event()
        self.writer = None
        self.dropped = 0
        self.gc_starts = {}

    def add(self, stage, entered, cpu, data=None):
        # Encoding into a bytes object keeps buffered records untracked by GC.
        row = {'tag':'DEBUG-mac70','stage':stage,'entered_ns':entered,
            'finished_ns':time.monotonic_ns(),'cpu_ns':time.thread_time_ns()-cpu,
            'thread_id':threading.get_ident(), 'thread_name':threading.current_thread().name}
        if data:
            row.update(data)
        if len(self.rows) == self.rows.maxlen:
            self.dropped += 1
        self.rows.append((REAL_DUMPS(row,separators=(',',':'))+'\n').encode())

    def gc_callback(self, phase, info):
        key = (threading.get_ident(),info['generation'])
        if phase == 'start':
            self.gc_starts[key] = (time.monotonic_ns(),time.thread_time_ns())
        elif key in self.gc_starts:
            entered,cpu = self.gc_starts.pop(key)
            self.add('gc',entered,cpu,dict(info))

    def start(self, path):
        path = Path(path)
        def drain():
            with path.open('xb') as stream:
                stream.write((REAL_DUMPS({'tag':'DEBUG-mac70','stage':'trace_start',
                    'monotonic_ns':time.monotonic_ns(),'capacity':self.rows.maxlen,
                    'original_method_returns_and_exceptions_preserved':True})+'\n').encode())
                while not self.finished.is_set() or self.rows:
                    batch = []
                    for unused in range(min(len(self.rows),4096)):
                        try:
                            batch.append(self.rows.popleft())
                        except IndexError:
                            break
                    if batch:
                        stream.write(b''.join(batch))
                        stream.flush()
                    self.finished.wait(.25)
                stream.write((REAL_DUMPS({'tag':'DEBUG-mac70','stage':'trace_end',
                    'monotonic_ns':time.monotonic_ns(),'dropped':self.dropped})+'\n').encode())
        self.writer = threading.Thread(target=drain,name='mac70-timing-writer',daemon=True)
        self.writer.start()
        gc.callbacks.append(self.gc_callback)

    def save(self, unused_path=None):
        if self.gc_callback in gc.callbacks:
            gc.callbacks.remove(self.gc_callback)
        self.finished.set()
        if self.writer:
            self.writer.join(timeout=3)


def install(port_type, reader_type):
    from p2b_backend_ros import runtime
    trace = Trace()

    for method, stage in [('_on_raw_command','raw_callback'),
                           ('_watchdog_tick','watchdog_callback'),
                           ('_on_body_pose','body_callback'),
                           ('_applied_evidence_ready','applied_ready')]:
        original = getattr(port_type,method)
        def observed(self, *args, _original=original, _stage=stage, **kwargs):
            entered,cpu = time.monotonic_ns(),time.thread_time_ns()
            before = self.gate.last_heartbeat_s
            data = {'heartbeat_before_s':before,'gate_before':self.gate.closed_reason}
            if _stage == 'raw_callback':
                message = args[0]
                identity = {key:getattr(message,key,None) for key in IDENTITY}
                owner = self.gate.owner
                data.update(identity=identity,identity_matches=(owner is not None and identity==owner.to_dict()),
                    source_stamp_ns=message.stamp.sec*1000000000+message.stamp.nanosec,
                    traj_id=message.traj_id)
            try:
                return _original(self,*args,**kwargs)
            finally:
                data.update(heartbeat_after_s=self.gate.last_heartbeat_s,
                            gate_after=self.gate.closed_reason)
                trace.add(_stage,entered,cpu,data)
        setattr(port_type,method,observed)

    original_read = reader_type.read
    def observed_read(self,*args,**kwargs):
        entered,cpu = time.monotonic_ns(),time.thread_time_ns()
        try:
            return original_read(self,*args,**kwargs)
        finally:
            trace.add('applied_read',entered,cpu)
    reader_type.read = observed_read

    original_state = runtime.NavigationHttpRuntime.state
    def observed_state(self,*args,**kwargs):
        entered,cpu = time.monotonic_ns(),time.thread_time_ns()
        try:
            return original_state(self,*args,**kwargs)
        finally:
            trace.add('http_state_snapshot',entered,cpu)
    runtime.NavigationHttpRuntime.state = observed_state

    def observed_dumps(data,*args,**kwargs):
        if not isinstance(data,dict) or 'pct' not in data or 'gate' not in data:
            return REAL_DUMPS(data,*args,**kwargs)
        entered,cpu = time.monotonic_ns(),time.thread_time_ns()
        result = None
        try:
            result = REAL_DUMPS(data,*args,**kwargs)
            return result
        finally:
            trace.add('http_state_json',entered,cpu,{
                'chars':None if result is None else len(result),
                'pct_history':len(data['pct'].get('plan_history',[]))})
    json.dumps = observed_dumps
    return trace
