from pathlib import Path
import json
P=Path(__file__).resolve().parent
previous=P.parent/'v27_native_regression01'
load=lambda path:json.loads(path.read_text())
result={'unmapped':{},'mapped':{},'continuations':{},'contract':load(P/'ground_contract.json')}
differences=[]
for name in ['empty','static_human','box','thin_wall','post','low_box','occluded_human','blocked_corridor']:
 a=load(previous/('unmapped_'+name+'.json'));b=load(P/('unmapped_'+name+'.json'))
 if a!=b:differences.append('unmapped_'+name)
 result['unmapped'][name]={'complete_output_identical_to_v27':a==b,'stale_rejected':b['stale_sensor_blocks_start'],'semantic_messages':b['semantic_messages']}
for name in ['box','low_box','low_box_near_wall','overhead','short_wall']:
 a=load(previous/('mapped_'+name+'.json'));b=load(P/('mapped_'+name+'.json'))
 if a!=b:differences.append('mapped_'+name)
 result['mapped'][name]={'complete_output_identical_to_v27':a==b}
for name in ['original','expired','v18','v19','v19_repeat','v21','v21_repeat','v23','v23_repeat','v26','v26_repeat']:
 d=load(P/(name+'.json'));negative=load(P/(name+'_negatives.json'));old=load(previous/(name+'.json'))
 assert all(d[k] for k in ['continued','boundary_pass','full_clear']) and d['accepted_xy_displacement_m']>0,name
 assert all(negative.values()),name
 if d!=old:differences.append(name)
 result['continuations'][name]={'accepted_xy_displacement_m':d['accepted_xy_displacement_m'],
  'v27_accepted_xy_displacement_m':old['accepted_xy_displacement_m'],'complete_output_identical_to_v27':d==old,
  'full_checks':True,'negatives':negative}
for first,second in [('v19','v19_repeat'),('v21','v21_repeat'),('v23','v23_repeat'),('v26','v26_repeat')]:
 a=dict(result['continuations'][first]);b=dict(result['continuations'][second])
 assert a==b and load(P/(first+'.json'))==load(P/(second+'.json')),first
assert '[BODY-SUPPORT] total=15' in (P/'body_support_contract.log').read_text()
assert result['contract']['single_source_not_or'] and result['contract']['legacy_empty_topic_unchanged'] and result['contract']['original_support_still_required']
assert load(P/'execution.json')['exit_code']==0
result.update(outputs_differing_from_v27=differences,component_scope_passed=not differences,physical_navigation_validated=False,
 known_mapped_low_protrusion_semantics='Pending user choice; reviewed separately and not covered by the eight unmapped fixture acceptance.')
(P/'review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'component_scope_passed':not differences,'differences':differences,'unmapped_cases':len(result['unmapped']),'mapped_cases':len(result['mapped']),'continuations':len(result['continuations'])}))
