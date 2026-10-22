"""Correct a misleading inherited logger name without changing numeric audits."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path('/home/ubuntu/sun/vla_v287_20261020')
EXP = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
AUDIT = EXP / 'audits/2026-10-20_v287_local_cost_crash'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    legacy = ROOT / 'evidence/initial_point_first_extract01'
    legacy.mkdir(exist_ok=False)
    rows = []
    for path in sorted((AUDIT / 'physical').glob('*/results/initial_collision_witness_audit.json')):
        data = json.loads(path.read_text())
        original_sha = sha(path)
        shutil.copy2(path, legacy / (data['case_id'] + '.json'))
        data['logged_initial_point_diagnostics'] = data.pop('actual_initial_collision_queries')
        data['source_clear_with_following_observed_diagnostic'] = data.pop('exact_query_static_source_clear_with_logged_observed_hit')
        data.update(diagnostic_only=True, collision_event_proven=False, numerical_results_changed=False,
            superseded_first_extract_sha256=original_sha,
            semantic_correction_source_sha256=sha(Path(__file__)),
            callsite='Frozen plan_manage/src/scan_replan_fsm.cpp1445-1447; unconditional recovery diagnostics for candidate_t0.9..1.2, including a+0.05m X diagnostic probe',
            claim='The inherited function name initial_spline_collision is not a rejection flag. These are logged diagnostic XYZ/yaw queries, not the optimizer control-point collision witnesses. Static support/source/raw numbers remain unchanged; no obstacle or stale-input cause is proved by these diagnostic logs alone.')
        path.write_text(json.dumps(data, indent=2) + '\n')
        rows.append({k: v for k, v in data.items() if k != 'rows'})
    (ROOT / 'evidence/initial_point_diagnostic_semantics02.json').write_text(json.dumps(dict(
        physics_steps=0, numerical_results_changed=False, old_interpretation_superseded=True,
        old_extracts_preserved=str(legacy), cases=rows), indent=2) + '\n')

if __name__ == '__main__':
    main()
