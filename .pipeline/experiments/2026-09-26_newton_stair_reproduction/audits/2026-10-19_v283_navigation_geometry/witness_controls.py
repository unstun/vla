"""Bind solid-excursion witnesses to actual applied control and pinned source."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
VERSION = HERE.parents[1] / 'versions/v283'
ROOT = Path('/home/sun/vla_exec/navigation_geometry_v283')
OUT = ROOT / 'candidate_diagnostics'
sys.path.insert(0, str(VERSION.parent / 'v196'))
from analyze_remote import Capture


def main():
    records = json.loads((OUT / 'recorded_summary.json').read_text())
    inventory = json.loads((VERSION / 'results/native_source_inventory.json').read_text())
    sources = {}
    for rel in ('src/scan_nav2_controller/include/scan_nav2_controller/tracking_node.hpp',
                'src/scan_nav2_controller/src/local_motion.cpp',
                'src/scan_nav2_controller/src/controller.cpp'):
        digest = hashlib.sha256((ROOT / 'native' / rel).read_bytes()).hexdigest()
        assert digest == inventory[rel]
        sources[rel] = digest
    witnesses = []
    for cid in sorted({r['case'] for r in records}):
        raw = Path('/home/sun/vla_exec/physical_runs_v283') / f'v283_{cid}_attempt01/runs/v283_{cid}_attempt01'
        capture = Capture(raw)
        telemetry = capture.rows('telemetry.jsonl')
        events = capture.rows('artifacts/reactive_observations.jsonl')
        for record in (r for r in records if r['case'] == cid):
            target = record['time_s']
            row = min(telemetry, key=lambda r: abs(r['physics_time_s'] - target))
            assert abs(row['physics_time_s'] - target) < .021
            previous = [r for r in events if r['event'] == 'gated_command' and r['clock_ns'] * 1e-9 <= target]
            witnesses.append(dict(case_id=cid, target_s=target,
                telemetry={k:row[k] for k in ('physics_time_s','effective_command','requested_command',
                    'command_reason','command_stale','stance_mode','policy_owns_joints','body_sensor')},
                latest_observed_gated_command=max(previous, key=lambda r:r['clock_ns']) if previous else None,
                reconstructed_curve=next(p for p in record['poses'] if p['role']=='planned_at_phase')))
        sources.update({cid+'/'+name:record['sha256'] for name,record in capture.sources.items()})
    result = dict(physics_steps=0, witnesses=witnesses, source_hashes=sources,
        native_manifest_sha256=hashlib.sha256((VERSION / 'native_manifest.json').read_bytes()).hexdigest(),
        analysis_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        phase_caveat='Elapsed time past published start is a nominal-phase reconstruction. The tracker freezes its internal phase during yaw control; no exact internal phase replay is claimed.')
    (OUT / 'control_witnesses.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps([dict(case_id=r['case_id'],time_s=r['target_s'],
        effective_command=r['telemetry']['effective_command'],stance=r['telemetry']['stance_mode']) for r in witnesses]))


if __name__ == '__main__':
    main()
