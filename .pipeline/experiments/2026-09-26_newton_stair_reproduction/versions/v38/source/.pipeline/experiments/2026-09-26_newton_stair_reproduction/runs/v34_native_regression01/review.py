"""Compare v34's (scan65) native regression outputs (JSON, query CSVs, negatives and logs) with v31's (scan64).

Adapted from runs/v31_native_regression03/review.py; v34 may change outputs where the added floor changes support.

Writes review.json. component_scope_passed requires all continuations accepted
with full gates and negatives, identical repeats, the contracts, an entry in
difference_explanations.json for every output file that differs from v31, and
an entry in log_difference_explanations.json for every log whose normalised
text differs from v31 (log_review.py, rerun here: v31's normalisation, plus
dropping v34's evidence_floor_fill lines), no stale entry in either file, and a
complete log comparison: at least one log, and every log present in both runs.
"""
from pathlib import Path
import json, subprocess, sys

P = Path(__file__).resolve().parent
previous = P.parent / 'v31_native_regression03'
load = lambda path: json.loads(path.read_text())
result = {'unmapped': {}, 'mapped': {}, 'continuations': {}, 'contract': load(P / 'ground_contract.json')}
differences = []
for name in ['empty', 'static_human', 'box', 'thin_wall', 'post', 'low_box', 'occluded_human', 'blocked_corridor']:
    a, b = load(previous / ('unmapped_' + name + '.json')), load(P / ('unmapped_' + name + '.json'))
    if a != b: differences.append('unmapped_' + name)
    result['unmapped'][name] = {'complete_output_identical_to_v31': a == b, 'stale_rejected': b['stale_sensor_blocks_start'],
                                'semantic_messages': b['semantic_messages']}
for name in ['box', 'low_box', 'low_box_near_wall', 'overhead', 'short_wall']:
    a, b = load(previous / ('mapped_' + name + '.json')), load(P / ('mapped_' + name + '.json'))
    if a != b: differences.append('mapped_' + name)
    result['mapped'][name] = {'complete_output_identical_to_v31': a == b}
accepted = True
for name in ['original', 'expired', 'v18', 'v19', 'v19_repeat', 'v21', 'v21_repeat', 'v23', 'v23_repeat', 'v26', 'v26_repeat']:
    d, negative, old = load(P / (name + '.json')), load(P / (name + '_negatives.json')), load(previous / (name + '.json'))
    full = all(d[k] for k in ['continued', 'boundary_pass', 'full_clear']) and d['accepted_xy_displacement_m'] > 0
    accepted = accepted and full and all(negative.values())
    if d != old: differences.append(name)
    same_queries = (P / (name + '_queries.csv')).read_bytes() == (previous / (name + '_queries.csv')).read_bytes()
    if not same_queries: differences.append(name + '_queries.csv')
    same_negatives = negative == load(previous / (name + '_negatives.json'))
    if not same_negatives: differences.append(name + '_negatives.json')
    result['continuations'][name] = {'accepted_xy_displacement_m': d['accepted_xy_displacement_m'],
                                     'v31_accepted_xy_displacement_m': old['accepted_xy_displacement_m'],
                                     'complete_output_identical_to_v31': d == old, 'query_csv_identical_to_v31': same_queries,
                                     'negatives_identical_to_v31': same_negatives,
                                     'full_checks': full, 'negatives': negative}
repeats = all(load(P / (a + '.json')) == load(P / (b + '.json'))
              for a, b in [('v19', 'v19_repeat'), ('v21', 'v21_repeat'), ('v23', 'v23_repeat'), ('v26', 'v26_repeat')])
body_support = '[BODY-SUPPORT] total=15' in (P / 'body_support_contract.log').read_text()
contract = result['contract']['single_source_not_or'] and result['contract']['legacy_empty_topic_unchanged'] and \
    result['contract']['original_support_still_required']
explanations_path = P / 'difference_explanations.json'
explanations = load(explanations_path) if explanations_path.exists() else {}
unexplained = [name for name in differences if not explanations.get(name)]
log_differences_path = P / 'log_differences_vs_v31.json'
subprocess.run([sys.executable, str(P / 'log_review.py'), str(previous), str(P), str(log_differences_path)],
               check=True, capture_output=True)
log_differences = sorted(load(log_differences_path))
log_explanations_path = P / 'log_difference_explanations.json'
log_explanations = load(log_explanations_path) if log_explanations_path.exists() else {}
unexplained_logs = [name for name in log_differences if not log_explanations.get(name)]
stale_log_explanations = sorted(set(log_explanations) - set(log_differences))
logs = lambda root: {str(path.relative_to(root)) for path in root.rglob('*.log') if 'build' not in path.relative_to(root).parts[0]}
# Guard against an empty or partial comparison: every v34 log needs its v31 counterpart and vice versa.
logs_compared = sorted(logs(P) & logs(previous))
logs_without_v31 = sorted(logs(P) - logs(previous))
v31_logs_missing = sorted(logs(previous) - logs(P))
stale_output_explanations = sorted(set(explanations) - set(differences))
result.update(all_continuations_accepted_with_full_gates=accepted, repeats_identical=repeats,
              body_support_contract=body_support, ground_contract=contract,
              execution_exit_zero=load(P / 'execution.json')['exit_code'] == 0,
              outputs_differing_from_v31=differences, unexplained_differences=unexplained,
              logs_differing_from_v31=log_differences, unexplained_log_differences=unexplained_logs,
              stale_log_explanations=stale_log_explanations, stale_output_explanations=stale_output_explanations,
              logs_compared=len(logs_compared), logs_without_v31_counterpart=logs_without_v31, v31_logs_missing=v31_logs_missing,
              component_scope_passed=accepted and repeats and body_support and contract and not unexplained and
              not stale_output_explanations and not unexplained_logs and not stale_log_explanations and
              bool(logs_compared) and not logs_without_v31 and not v31_logs_missing and
              load(P / 'execution.json')['exit_code'] == 0,
              physical_navigation_validated=False,
              known_mapped_low_protrusion_semantics='Pending user choice; reviewed separately and not covered by the eight unmapped fixture acceptance.')
(P / 'review.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'component_scope_passed': result['component_scope_passed'], 'accepted': accepted, 'repeats': repeats,
                  'differences': differences, 'unexplained': unexplained, 'log_differences': log_differences,
                  'unexplained_logs': unexplained_logs, 'stale_log_explanations': stale_log_explanations,
                  'stale_output_explanations': stale_output_explanations, 'logs_compared': len(logs_compared),
                  'logs_without_v31_counterpart': logs_without_v31, 'v31_logs_missing': v31_logs_missing}))
