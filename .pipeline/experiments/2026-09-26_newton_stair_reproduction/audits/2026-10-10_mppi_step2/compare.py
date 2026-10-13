"""Apply the predeclared keep/park rule to all returned physical trials."""
from pathlib import Path
import hashlib
import json
import statistics

HERE=Path(__file__).resolve().parent
rows=[]
for path in sorted((HERE/'physical').glob('*/outcome.json')):
    outcome=json.loads(path.read_text())
    m=outcome.get('metrics',{})
    t=m.get('terminal') or {}
    navigation=(outcome['execution_exit']==0 and outcome.get('retention')=='completed'
        and t.get('backend_terminal_status')=='FINISHED'
        and t.get('note')=='native arrival and measured PD hold'
        and m.get('state_copyback_verified') is True and m.get('fallen') is False)
    rows.append({'run':outcome['tag'],'variant':outcome['variant'],'navigation_passed':navigation,
                 'metrics':m,'outcome_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
groups={name:[r for r in rows if r['variant']==name] for name in ('baseline','candidate')}
summary={'versions':{'baseline':'v122','candidate':'v126'},'host':'gpu5070ti','physics':'CPU Newton',
         'rows':rows,'trials_per_variant':{k:len(v) for k,v in groups.items()},
         'limits':['At most two trials per variant cannot establish population reliability.',
                   'Longest pause includes the deliberate goal hold.',
                   'Failure in a planning round does not imply navigation failure.',
                   'No Jetson or real-robot qualification; no hard 60 ms deadline.']}
if any(not r['navigation_passed'] for r in groups['candidate']):
    summary.update(decision='park',reason='Candidate navigation or execution failed; retain all evidence.')
elif all(len(v)==2 and all(r['navigation_passed'] for r in v) for v in groups.values()):
    medians={name:{'p95_ms':statistics.median(r['metrics']['planning']['solve_ms']['p95'] for r in group),
                  'longest_pause_s':statistics.median(r['metrics']['longest_pause_sim_s'] for r in group),
                  'navigation_duration_s':statistics.median(r['metrics']['navigation_sim_duration_s'] for r in group)}
             for name,group in groups.items()}
    p95=medians['candidate']['p95_ms']<=1.10*medians['baseline']['p95_ms']
    pause=medians['candidate']['longest_pause_s']<=medians['baseline']['longest_pause_s']+1.0
    summary.update(medians=medians,p95_gate=p95,pause_gate=pause,
                   decision='keep' if p95 and pause else 'park',
                   reason='Apply declared median P95 <= 1.10x and pause <= baseline + 1 second.')
else:
    summary.update(decision='incomplete',reason='Comparison requires two completed comparable pairs.')
summary['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
(HERE/'comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='rows'},indent=2))
