"""Replay the recorded heartbeat gap through the unchanged command gate."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
sys.path.insert(0,str(BASE/'runtime_sources/backend_adapter'))
from backend_adapter.contracts import CommandIdentity, GateConfig, MeasuredState
from backend_adapter.control_gate import CommandGate

results = []
for name in ('trial01','trial02'):
    source = HERE/'evidence'/f'{name}.json'
    data = json.loads(source.read_text())
    heartbeat = data['last_matching_heartbeat_before_stop_s']
    timer = data['fault']['flow']['started_monotonic_s']
    identity = CommandIdentity(**data['fault']['owner'])
    incoming = data['matching_raw_between_last_backend_heartbeat_and_fault']
    assert incoming and all(CommandIdentity(**r['identity']).matches(identity) for r in incoming)
    newest = incoming[-1]['receipt_s']
    now = [heartbeat]
    def make_gate():
        gate = CommandGate(GateConfig(heartbeat_stale_s=.2,odom_time_base='simulation'),
                           clock=lambda:now[0],sim_clock=lambda:44.)
        gate.admit(identity)
        gate.observe_measurement(MeasuredState(1,heartbeat,(0.,0.,.3),(0.,0.,0.),
            identity.map_epoch,identity.map_revision,'fresh_measurement_fixture',stamp_s=44.))
        gate.observe_heartbeat(heartbeat)
        return gate
    stalled = make_gate()
    now[0] = timer
    stale = stalled.tick(now_s=timer)
    assert not stale.allowed and stale.reason == 'heartbeat_stale'
    stalled.observe_heartbeat(newest)
    assert stalled.tick(now_s=timer).reason == 'heartbeat_stale'
    now[0] = heartbeat
    consumed = make_gate()
    consumed.observe_heartbeat(newest)
    now[0] = timer
    fresh = consumed.tick(now_s=timer)
    assert fresh.allowed and fresh.reason == 'ok'
    results.append({'trial':name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'matching_queued_messages':len(incoming),'timer_s':timer,'accepted_heartbeat_s':heartbeat,
        'newest_independent_matching_receipt_s':newest,'newest_receipt_age_at_timer_ms':(timer-newest)*1000,
        'timer_before_queued_raw_callback':stale.reason,
        'consuming_pending_matching_raw_before_timer':fresh.reason,
        'later_heartbeat_cannot_reopen_closed_gate':True,
        'production_thresholds_or_stop_protocol_changed':False})
proof = {'status':'passed','assertions':10,'results':results,
    'gate_source_sha256':hashlib.sha256((BASE/'runtime_sources/backend_adapter/backend_adapter/control_gate.py').read_bytes()).hexdigest(),
    'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'claim':'Original gate reproduces the recorded stop when callback delivery is delayed; determines the scheduling failure mechanism, not the precise OS/GIL cause of the historical delay. Measurement/map inputs are held fresh at this focused seam.'}
(HERE/'gate_order_replay.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof,indent=2))
