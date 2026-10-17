"""Audit a closed Mac attempt without modifying its archived raw files (Option B direct Nav2 + SCAN)."""
from pathlib import Path
import argparse
import json
from analyze_remote import analyze, Capture
from verify_full_route import verify

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--trial', type=Path, required=True)
    a = p.parse_args()
    root = a.trial / 'runs' / a.trial.name
    out = HERE / 'results' / a.trial.name
    out.mkdir(parents=True, exist_ok=False)
    try:
        analyze(root, out, True)
    except Exception as e:
        result = {'run': root.name, 'full_qualification': False, 'analysis_error': repr(e),
                  'claim': 'Interrupted run; preserve archived raw evidence'}
        (out / 'outcome.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)
        return
    try:
        route = verify(root)
    except Exception as e:
        route = {'passed': False, 'run': root.name, 'error': repr(e)}
    (out / 'full_route_verification.json').write_text(json.dumps(route, indent=2) + '\n')
    capture = Capture(root)
    obs = capture.rows('artifacts/reactive_observations.jsonl')
    pct_routes = [r for r in obs if r['event'] == 'pct_route']
    bsplines = [r for r in obs if r['event'] == 'bspline']
    outcome = {
        'run': root.name,
        'arrived': route['passed'],
        'pct_route_publications': len(pct_routes),
        'bspline_publications': len(bsplines),
        'command_transport': 'direct_nav2_twist',
        'full_qualification': route['passed'] and len(pct_routes) > 0 and len(bsplines) > 0,
    }
    (out / 'outcome.json').write_text(json.dumps(outcome, indent=2) + '\n')
    print(json.dumps(outcome), flush=True)


if __name__ == '__main__':
    main()
