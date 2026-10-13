"""Analyze every retained pilot and the predeclared fresh comparison."""
from pathlib import Path
import hashlib,json,math,subprocess,sys
T=Path('/data/sun/vla_mppi_20261009');B=Path(__file__).resolve().parents[2];H=Path(__file__).resolve().parent
sys.path.insert(0,str(B/'versions/v127'))
from analyze_remote import Capture
sys.path.insert(0,str(B/'audits/2026-10-10_nav2_recovery'))
from analyze_recovery_proofs import analyze as proofs
from analyze_events import analyze as events
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 assert not subprocess.check_output(['docker','ps','--format','{{.Names}}'],text=True).strip()
 progress=json.loads((T/'results/recovery_v139_02_repeats/progress.json').read_text());assert progress['state']=='completed' and len(progress['completed'])==12
 out=T/'results/v133_posture/final_analysis01';out.mkdir(exist_ok=False)
 tags=[f'{v}_candidate_attempt{i:02d}' for v in ['v134','v135','v136','v137','v138','v139'] for i in range(1,4)]
 tags += [r['tag'] for r in progress['completed']]
 rows=[];proof_rows=[];event_rows=[]
 for tag in tags:
  ver=tag.split('_')[0];root=T/'results'/('recovery_'+ver+('_02' if ver=='v139' else ''))/'comparison'/tag
  f=root/'outcome.json';o=json.loads(f.read_text());m=o['metrics'];c=Capture(T/'trials'/tag/'runs'/tag)
  log=c.read('nav2.log').splitlines();observations=c.rows('artifacts/reactive_observations.jsonl')
  accepted=[r['data']['generation'] for r in observations if r['event']=='scan_admission' and r['data'].get('consumer')=='fsm' and r['data'].get('status')=='accepted']
  row={'run':tag,'native':('v137' if '_baseline_' in tag else ver),'arm':('baseline' if '_baseline_' in tag else 'candidate'),'pilot':tag not in [r['tag'] for r in progress['completed']],
       'terminal':m['terminal']['backend_terminal_status'],'fallen':m['fallen'],'copyback':m['state_copyback_verified'],'retention':o['retention'],'path_m':m['measured_path_m'],'end_sim_s':m['actual_physics_end_s'],
       'final_pose':m['final_body_xyz_m'],'minimum_base_up_z':m['minimum_base_up_z'],'longest_pause_s':m['longest_pause_sim_s'],'pauses':m['pauses_over_1s'],'planning':m['planning'],'outcome_sha256':sha(f),
       'accepted_generations':sorted(set(accepted)),'sampled_feedback_rounds':sum('V139_SAMPLED_REBOUND' in l for l in log),'final_feedback_rounds':sum('V139_FINAL_FEEDBACK' in l for l in log),
       'failed_curve_checks':sum('final_spline_rejected' in l for l in log),'source':c.sources}
  rows.append(row);proof_rows.append(proofs(tag));event_rows.append(events(tag))
  print(json.dumps({'run':tag,'terminal':row['terminal'],'replacement_proofs':proof_rows[-1]['all_replacements_have_recorded_proof']}),flush=True)
 fresh=[r for r in rows if not r['pilot']];groups={}
 for arm in ['baseline','candidate']:
  r=[x for x in fresh if x['arm']==arm];assert len(r)==6
  groups[arm]={'runs':6,'arrivals':sum(x['terminal']=='FINISHED' for x in r),'falls':sum(x['fallen'] for x in r),'tags':[x['run'] for x in r]}
 candidate_tags=groups['candidate']['tags'];p=[x for x in proof_rows if x['run'] in candidate_tags]
 gate=groups['candidate']['arrivals']==6 and groups['candidate']['falls']==0 and all(x['all_replacements_have_recorded_proof'] for x in p)
 result={'groups':groups,'candidate_gate_passed':gate,'candidate_replacements':sum(x['replacement_owners'] for x in p),'all_candidate_replacement_proofs_passed':all(x['all_replacements_have_recorded_proof'] for x in p),'rows':rows,'script_sha256':sha(Path(__file__)),
         'boundary':'Fixed physical scenario on gpu5070ti CPU Newton/Foxy. Pilots and fresh comparison have separate denominators. No general success-rate, 30 Hz, Jetson or robot acceptance.'}
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');(out/'stop_proofs.json').write_text(json.dumps({'runs':proof_rows},indent=2)+'\n');(out/'events.json').write_text(json.dumps({'runs':event_rows},indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
if __name__=='__main__':main()
