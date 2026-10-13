"""Post-freeze analysis for trial02 with the frozen backend dependency restored."""
from pathlib import Path
import importlib.util
import json

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('frozen_v47_analysis',HERE/'analyze_trial.py')
analysis=importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def main():
    output=HERE/'analysis'
    results={}
    for version,run in [('v45','v45_realtime_preview01'),('v47','v47_realtime_trial02')]:
        metrics,rounds=analysis.analyze(run)
        results[version]=metrics
        (output/(version+'_qualified_rounds.json')).write_text(json.dumps(rounds,indent=2)+'\n')
    baseline=results['v45']['actual_local_attempt_hz']
    results['comparison']=dict(local_attempt_frequency_change_percent=100*(results['v47']['actual_local_attempt_hz']/baseline-1),
        limitation='Separate live trajectories with the same selected source/configuration outside Candidate 1; no paired executable replay of v45 live states.',
        excluded_run='v47_realtime_trial01: missing backend dependency caused old-backend fallback, absent 1 Hz global refresh and no preserved Nav2 runtime behavior.')
    assert results['v47']['global_refresh_samples']>0,'Qualified run must expose global refresh evidence'
    (output/'qualified_metrics.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps({v:{k:r[k] for k in ['actual_local_attempt_hz','local_solve_ms','first_seed_failure_fraction','window_hint_rounds','measured_path_length_m','terminal_status']} for v,r in results.items() if v!='comparison'},indent=2))


if __name__=='__main__':
    main()
