"""Extract compact, hash-bound direct stop evidence from the closed candidate."""
from pathlib import Path
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
sys.path.insert(0,str(BASE/'versions/v127'))
from analyze_remote import Capture
TASK=Path('/data/sun/vla_mppi_20261009')
assert HERE.is_relative_to(TASK/'repo')
root=TASK/'trials/v127_candidate_attempt01/runs/v127_candidate_attempt01'
capture=Capture(root)
text=capture.read('nav2.log');lines=text.splitlines()
keys=('Failed to make progress','scan_safety_evidence_stale','scan_trajectory_missing',
      'Navigation failed','Controller native validation rejected','SCAN evidence rejected now=')
events=[{'line':i+1,'text':line} for i,line in enumerate(lines) if any(key in line for key in keys)]
# Keep all terminal failure events, with the exact sensor-age evidence nearby.
last_events=events[-30:]
maximum=json.loads((TASK/'results/step3_v127/comparison/v127_candidate_attempt01/max_round.json').read_text())
segment=lines[maximum['start_line']-1:maximum['end_line']]
round_diagnostics=[json.loads(line.split('V122_PLANNING_OUTCOME ',1)[1])
                   for line in segment if 'V122_PLANNING_OUTCOME ' in line]
assert len(round_diagnostics)==1
backend=capture.json('backend_latest.json')
result={'candidate':'v127_candidate_attempt01','direct_sequence':last_events,
        'maximum_round':maximum,'maximum_round_diagnostic':round_diagnostics[0],
        'terminal_results':backend.get('terminal_results'),
        'claim':'Direct terminal events are recorded without assuming the same cause as the previous adaptation. '
                'The paired physical trial does not isolate a causal state-equivalent explanation for the regression.',
        'source':capture.sources,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
out=TASK/'results/step3_v127/postmortem.json'
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'events':len(last_events),'output':str(out)}))
