"""Compare v48 warm initialization with qualified v47 trial02."""
from pathlib import Path
import importlib.util
import json
import re
from collections import Counter

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('frozen_v47_analysis',HERE.parent/'v47/analyze_trial.py')
core=importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


def main():
    output=HERE/'analysis';output.mkdir(exist_ok=True)
    result={}
    for version,run in [('v47','v47_realtime_trial02'),('v48','v48_realtime_trial01')]:
        metrics,rounds=core.analyze(run)
        log_path=core.BASE/'runs'/run/'scan.log';lines=log_path.read_text().splitlines()
        for row in rounds:
            text='\n'.join(lines[row['start_line']-1:row['end_line']])
            row['warm_selections']=len(re.findall(r'V48_WARM_SEED selected=1',text))
            row['warm_accepts']=text.count('V48_WARM_RESULT accepted=1')
            row['warm_graph_fallbacks']=text.count('V48_WARM_RESULT accepted=0 graph_fallback=1')
        all_text='\n'.join(lines)
        metrics['warm_selected_attempts']=sum(r['warm_selections'] for r in rounds)
        metrics['warm_accepted_attempts']=sum(r['warm_accepts'] for r in rounds)
        metrics['warm_graph_fallbacks']=sum(r['warm_graph_fallbacks'] for r in rounds)
        metrics['warm_rejection_reasons']=dict(Counter(re.findall(r'V48_WARM_SEED selected=0 reason=(\w+)',all_text)))
        metrics['warm_validation_ms']=core.distribution([float(t) for t in re.findall(r'V48_WARM_SEED selected=\d reason=\w+ nodes=\d+ wall_ms=([\d.]+)',all_text)])
        metrics['warm_round_groups']={}
        for name,group in [('warm_only',[r for r in rounds if r['warm_accepts'] and not r['warm_graph_fallbacks']]),('warm_then_graph',[r for r in rounds if r['warm_graph_fallbacks']]),('no_warm_accept',[r for r in rounds if not r['warm_accepts'] and not r['warm_graph_fallbacks']])]:
            metrics['warm_round_groups'][name]={'rounds':len(group),'solve_ms':core.distribution([r['wall_s']*1000 for r in group])}
        result[version]=metrics
        (output/(version+'_rounds.json')).write_text(json.dumps(rounds,indent=2)+'\n')
    a,b=result['v47'],result['v48']
    assert b['global_refresh_samples']>0,'Require actual preserved global refresh'
    result['comparison']={'local_frequency_percent_change':100*(b['actual_local_attempt_hz']/a['actual_local_attempt_hz']-1),'p95_percent_change':100*(b['local_solve_ms']['p95']/a['local_solve_ms']['p95']-1),'p99_percent_change':100*(b['local_solve_ms']['p99']/a['local_solve_ms']['p99']-1),'limitation':'Separate live trajectories with identical source/configuration outside Candidate 2; recorded paired native fixtures do not cover the complete live distribution.'}
    (output/'metrics.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({version:{k:row[k] for k in ['actual_local_attempt_hz','local_solve_ms','warm_selected_attempts','warm_accepted_attempts','warm_graph_fallbacks','measured_path_length_m','terminal_status']} for version,row in result.items() if version!='comparison'},indent=2))


if __name__=='__main__':main()
