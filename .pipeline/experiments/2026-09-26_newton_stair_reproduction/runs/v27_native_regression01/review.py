from pathlib import Path
import json
P=Path(__file__).resolve().parent
previous=P.parent/'v24_native_regression01'
result={'unmapped':{},'continuations':{},'contract':json.loads((P/'ground_contract.json').read_text())}
for name in ['empty','static_human','box','thin_wall','post','low_box','occluded_human','blocked_corridor']:
 a=json.loads((previous/('unmapped_'+name+'.json')).read_text());b=json.loads((P/('unmapped_'+name+'.json')).read_text())
 assert a==b,name
 result['unmapped'][name]={'complete_output_identical':True,'stale_rejected':b['stale_sensor_blocks_start'],'semantic_messages':b['semantic_messages']}
for name in ['original','expired','v18','v19','v19_repeat','v21','v21_repeat','v23','v23_repeat','v26','v26_repeat']:
 d=json.loads((P/(name+'.json')).read_text());negative=json.loads((P/(name+'_negatives.json')).read_text())
 assert all(d[k] for k in ['continued','boundary_pass','full_clear']) and d['accepted_xy_displacement_m']>0,name
 assert all(negative.values()),name
 result['continuations'][name]={'accepted_xy_displacement_m':d['accepted_xy_displacement_m'],'full_checks':True,'negatives':negative}
for first,second in [('v19','v19_repeat'),('v21','v21_repeat'),('v23','v23_repeat'),('v26','v26_repeat')]:
 assert result['continuations'][first]==result['continuations'][second]
assert '[BODY-SUPPORT] total=15' in (P/'body_support_contract.log').read_text()
assert result['contract']['single_source_not_or'] and result['contract']['legacy_empty_topic_unchanged'] and result['contract']['original_support_still_required']
assert json.loads((P/'execution.json').read_text())['exit_code']==0
result.update(component_scope_passed=True,physical_navigation_validated=False,known_mapped_low_protrusion_semantics='Pending user choice; reviewed separately and not covered by the eight unmapped fixture acceptance.')
(P/'review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'component_scope_passed':True,'unmapped_cases':len(result['unmapped']),'continuations':len(result['continuations']),'new_stop_accepted_m':result['continuations']['v26']['accepted_xy_displacement_m']}))
