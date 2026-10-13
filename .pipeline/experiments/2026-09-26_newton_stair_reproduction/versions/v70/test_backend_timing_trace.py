"""Actual backend callback/JSON seam: tracing preserves command and failures."""
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace as NS
import unittest

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BASE/'runtime_sources/backend_adapter'))
sys.path.insert(0,str(BASE/'versions/v59/backend_ros'))
from backend_adapter.contracts import CommandIdentity, GateConfig, MeasuredState
from backend_adapter.control_gate import CommandGate
from backend_adapter.applied_evidence import AppliedEvidenceReader
from p2b_backend_ros.node import RosScanPort
from backend_timing_trace import install, REAL_DUMPS


class TraceTests(unittest.TestCase):
    def test_actual_raw_gate_error_and_json_behavior(self):
        trace = install(RosScanPort,AppliedEvidenceReader)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'trace.jsonl'
            trace.start(path)
            identity = CommandIdentity('diagnostic-test',1,'request','goal','route','command',1,'map',1)
            gate = CommandGate(GateConfig())
            gate.admit(identity)
            gate.observe_measurement(MeasuredState(1,time.monotonic(),(0.,0.,.3),(0.,0.,0.),'map',1,'fixture'))
            port = RosScanPort.__new__(RosScanPort)
            port.gate = gate
            port.config = {'run_id':'diagnostic-test'}
            port.adapter = NS(applied_reader=None)
            port._owner_first_heartbeat_s = None
            port._last_raw_command_s = None
            port._faults = []
            port.node = NS(get_logger=lambda:NS(warn=lambda unused:None))
            messages = []
            port.Twist = lambda:NS(linear=NS(x=0.,y=0.,z=0.),angular=NS(x=0.,y=0.,z=0.))
            port.gated_pub = NS(publish=messages.append)
            msg = NS(**identity.to_dict(),stamp=NS(sec=1,nanosec=0),traj_id=1,
                     twist=NS(linear=NS(x=.3,y=.1),angular=NS(z=.05)))
            self.assertIsNone(port._on_raw_command(msg))
            self.assertEqual((messages[-1].linear.x,messages[-1].linear.y,messages[-1].angular.z),(.3,.1,.05))
            self.assertEqual(gate.closed_reason,'open')
            msg.run_id = ''
            port._on_raw_command(msg)
            self.assertEqual(port._last_block_reason,'invalid_raw_identity')
            self.assertEqual((messages[-1].linear.x,messages[-1].linear.y,messages[-1].angular.z),(0.,0.,0.))
            self.assertEqual(port._faults[-1]['kind'],'invalid_raw_identity')
            missing = AppliedEvidenceReader(Path(directory)/'missing.json')
            with self.assertRaisesRegex(Exception,'applied_snapshot_missing'):
                missing.read()
            data = {'pct':{'plan_history':[[1.,2.,3.]]},'gate':{'reason':'open'}}
            self.assertEqual(json.dumps(data,sort_keys=True),REAL_DUMPS(data,sort_keys=True))
            trace.save()
            rows = [json.loads(s) for s in path.read_text().splitlines()]
            self.assertEqual(rows[-1]['stage'],'trace_end')
            self.assertEqual(rows[-1]['dropped'],0)
            self.assertEqual(sum(r['stage']=='raw_callback' for r in rows),2)
            raw = next(r for r in rows if r['stage']=='raw_callback')
            self.assertTrue(raw['identity_matches'])
            self.assertEqual(raw['gate_after'],'open')
            self.assertTrue(any(r['stage']=='applied_read' for r in rows))
            self.assertTrue(any(r['stage']=='http_state_json' for r in rows))


if __name__ == '__main__':
    unittest.main()
