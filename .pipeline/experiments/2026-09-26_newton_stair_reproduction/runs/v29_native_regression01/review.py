"""Compare v29's native regression outputs (JSON and query CSVs) with v28's; every difference needs an explanation.

Writes review.json. component_scope_passed requires all continuations accepted
with full gates and negatives, identical repeats, the contracts, and an entry in
difference_explanations.json for every output that differs from v28.
"""
from pathlib import Path
import json

P = Path(__file__).resolve().parent
previous = P.parent / 'v28_native_regression01'
load = lambda path: json.loads(path.read_text())
result = {'unmapped': {}, 'mapped': {}, 'continuations': {}, 'contract': load(P / 'ground_contract.json')}
differences = []
for name in ['empty', 'static_human', 'box', 'thin_wall', 'post', 'low_box', 'occluded_human', 'blocked_corridor']:
    a, b = load(previous / ('unmapped_' + name + '.json')), load(P / ('unmapped_' + name + '.json'))
    if a != b: differences.append('unmapped_' + name)
    result['unmapped'][name] = {'complete_output_identical_to_v28': a == b, 'stale_rejected': b['stale_sensor_blocks_start'],
                                'semantic_messages': b['semantic_messages']}
for name in ['box', 'low_box', 'low_box_near_wall', 'overhead', 'short_wall']:
    a, b = load(previous / ('mapped_' + name + '.json')), load(P / ('mapped_' + name + '.json'))
    if a != b: differences.append('mapped_' + name)
    result['mapped'][name] = {'complete_output_identical_to_v28': a == b}
accepted = True
for name in ['original', 'expired', 'v18', 'v19', 'v19_repeat', 'v21', 'v21_repeat', 'v23', 'v23_repeat', 'v26', 'v26_repeat']:
    d, negative, old = load(P / (name + '.json')), load(P / (name + '_negatives.json')), load(previous / (name + '.json'))
    full = all(d[k] for k in ['continued', 'boundary_pass', 'full_clear']) and d['accepted_xy_displacement_m'] > 0
    accepted = accepted and full and all(negative.values())
    if d != old: differences.append(name)
    same_queries = (P / (name + '_queries.csv')).read_bytes() == (previous / (name + '_queries.csv')).read_bytes()
    if not same_queries: differences.append(name + '_queries.csv')
    result['continuations'][name] = {'accepted_xy_displacement_m': d['accepted_xy_displacement_m'],
                                     'v28_accepted_xy_displacement_m': old['accepted_xy_displacement_m'],
                                     'complete_output_identical_to_v28': d == old, 'query_csv_identical_to_v28': same_queries,
                                     'full_checks': full, 'negatives': negative}
repeats = all(load(P / (a + '.json')) == load(P / (b + '.json'))
              for a, b in [('v19', 'v19_repeat'), ('v21', 'v21_repeat'), ('v23', 'v23_repeat'), ('v26', 'v26_repeat')])
body_support = '[BODY-SUPPORT] total=15' in (P / 'body_support_contract.log').read_text()
contract = result['contract']['single_source_not_or'] and result['contract']['legacy_empty_topic_unchanged'] and \
    result['contract']['original_support_still_required']
explanations_path = P / 'difference_explanations.json'
explanations = load(explanations_path) if explanations_path.exists() else {}
unexplained = [name for name in differences if not explanations.get(name)]
result.update(all_continuations_accepted_with_full_gates=accepted, repeats_identical=repeats,
              body_support_contract=body_support, ground_contract=contract,
              execution_exit_zero=load(P / 'execution.json')['exit_code'] == 0,
              outputs_differing_from_v28=differences, unexplained_differences=unexplained,
              component_scope_passed=accepted and repeats and body_support and contract and not unexplained and
              load(P / 'execution.json')['exit_code'] == 0,
              physical_navigation_validated=False,
              known_mapped_low_protrusion_semantics='Pending user choice; reviewed separately and not covered by the eight unmapped fixture acceptance.')
(P / 'review.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'component_scope_passed': result['component_scope_passed'], 'accepted': accepted, 'repeats': repeats,
                  'differences': differences, 'unexplained': unexplained}))
