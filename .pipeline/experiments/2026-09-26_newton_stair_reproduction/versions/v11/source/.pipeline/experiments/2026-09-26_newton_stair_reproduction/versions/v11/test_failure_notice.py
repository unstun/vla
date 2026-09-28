"""Exercise the actual receiver callback and its existing command gate."""
from pathlib import Path
from types import SimpleNamespace
import dataclasses
import sys
import threading
import unittest

BASE=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(BASE/'runtime_sources/backend_ros'),str(BASE/'runtime_sources/backend_adapter')]
from backend_adapter.contracts import CommandIdentity
from backend_adapter.control_gate import CommandGate
from p2b_backend_ros.node import RosScanPort
from p2b_backend_ros.runtime import _gate_fault_reason


class Publisher:
    def __init__(self):self.messages=[]
    def publish(self,message):self.messages.append(message)

def twist():
    return SimpleNamespace(linear=SimpleNamespace(x=0.,y=0.),angular=SimpleNamespace(z=0.))

def fixture():
    port=object.__new__(RosScanPort)
    owner=CommandIdentity('run',1,'request','goal','route','command',1,'map',1)
    port.gate=CommandGate();port.gate.admit(owner)
    port._condition=threading.Condition();port._admissions=[]
    port._last_admission=None;port._last_block_reason='open';port._faults=[]
    port.Twist=twist;port.gated_pub=Publisher()
    return port,owner

def notice(owner,**changes):
    payload={**dataclasses.asdict(owner),'consumer':'fsm','status':'rejected',
             'message':'native_replan_exhausted','hold_confirmed':False,
             'measured_stillness_confirmed':False}
    payload.update(changes)
    return SimpleNamespace(**payload)

class FailureNoticeTests(unittest.TestCase):
    def test_current_owner_native_failure_closes_without_claiming_hold(self):
        port,owner=fixture();port._on_admission(notice(owner))
        self.assertEqual(port.gate.closed_reason,'native_replan_exhausted')
        self.assertEqual(_gate_fault_reason(port.gate.snapshot()),'native_replan_exhausted')
        self.assertFalse(port.gate.hold_ack)
        self.assertEqual(len(port.gated_pub.messages),1)
        self.assertEqual(port.gated_pub.messages[0].linear.x,0.)
        self.assertEqual(port.gated_pub.messages[0].linear.y,0.)
        self.assertEqual(port.gated_pub.messages[0].angular.z,0.)

    def test_unrelated_or_stale_notices_do_not_close_owner(self):
        for change in [{'generation':2},{'run_id':'other'},{'command_id':'old'},
                       {'consumer':'controller'},{'status':'accepted'},
                       {'message':'ordinary_route_rejection'}]:
            with self.subTest(change=change):
                port,owner=fixture();port._on_admission(notice(owner,**change))
                self.assertEqual(port.gate.closed_reason,'open')
                self.assertFalse(port.gated_pub.messages)

    def test_cancel_precedence(self):
        port,owner=fixture();port.gate.request_cancel(owner,'cancel_by_user')
        port._on_admission(notice(owner))
        self.assertEqual(port.gate.closed_reason,'cancel_by_user')

    def test_no_owner(self):
        port,owner=fixture();port.gate.owner=None
        port._on_admission(notice(owner))
        self.assertEqual(port.gate.closed_reason,'open')

if __name__=='__main__':unittest.main()
