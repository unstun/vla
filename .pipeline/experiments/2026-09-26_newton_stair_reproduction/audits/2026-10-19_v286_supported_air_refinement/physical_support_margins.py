"""Audit actual hard support clearance separately from the retained ENV atlas."""
from pathlib import Path
import hashlib
import csv
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
BASE = Path('/data/sun/vla_mppi_20261009')
IMAGE = 'sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4'


def audit(case):
    directory = HERE / 'physical' / case
    results = directory / 'results'
    assert (results / 'local_video_delivery.json').is_file()
    target = results / 'physical_support_margins.jsonl'
    shell = ('source /opt/ros/foxy/setup.bash && '
             'source /task/recovery_v188/install/setup.bash && '
             'source /task/command_continuity_v206_20261015/install/setup.bash && '
             'source /work/install/setup.bash && '
             '/audit/margin_build/edge_diagnostic /audit/body_poses.txt')
    command = ['docker', 'run', '--rm', '--pull=never', '--cpus=2', '--memory=3g',
               '--user', f'{os.getuid()}:{os.getgid()}',
               '-v', str(BASE) + ':/task:ro',
               '-v', str(Path('/home/sun/vla_exec/supported_air_refinement_v286/native')) + ':/work:ro',
               '-v', str(directory) + ':/audit:ro',
               '--entrypoint', '/bin/bash', IMAGE, '-c', shell]
    if not target.exists():
        data = subprocess.check_output(command, text=True, timeout=120)
        rows = [json.loads(line) for line in data.splitlines()]
        assert rows and all(abs(r['hard_radius_m'] - .35) < 1e-12 for r in rows)
        with target.open('x') as output:
            output.write(data)
    rows = [json.loads(line) for line in target.read_text().splitlines()]
    times = [float(row['case_id']) for row in rows]
    expected_times = [float(line.split()[0]) for line in (directory / 'body_poses.txt').read_text().splitlines()]
    assert times == expected_times
    assert all(a < b for a, b in zip(times, times[1:]))
    with (results / 'body_margins.csv').open() as stream:
        previous = list(csv.DictReader(stream))
    assert len(previous) == len(rows)
    for old, new in zip(previous, rows):
        assert int(old['static_support_verdict']) == new['hard_support_verdict']
        assert abs(float(old['extra_edge_margin_m']) - new['ENV_edge_m']) < 1e-12
    windows = json.loads((results / 'window_audit.json').read_text())['windows']
    summary = {}
    for name, window in windows.items():
        lo, hi = window['measured']['window_s']
        part = [r for r, t in zip(rows, times) if lo <= t < hi]
        free = [r for r in part if r['hard_support_verdict'] == 0]
        summary[name] = dict(window_s=[lo, hi], samples=len(part), free_samples=len(free),
            minimum_gap_all_samples_m=min((r['support_gap_extra_margin_m'] for r in part), default=None),
            minimum_gap_on_free_support_m=min((r['support_gap_extra_margin_m'] for r in free), default=None),
            verdict_counts={str(v): sum(r['hard_support_verdict'] == v for r in part)
                            for v in sorted({r['hard_support_verdict'] for r in part})},
            ENV_atlas_minimum_m=min((r['atlas_only_edge_m'] for r in part), default=None))
    report = dict(case_id=case, physics_steps=0, radius_m=.35, reporting_cap_m=.15,
        samples=len(rows), windows=summary, existing_verdict_and_ENV_parity=True,
        pose_sha256=hashlib.sha256((directory / 'body_poses.txt').read_bytes()).hexdigest(),
        native_probe_sha256=hashlib.sha256((directory / 'margin_build/edge_diagnostic').read_bytes()).hexdigest(),
        native_manifest_sha256=hashlib.sha256((HERE.parents[1] / 'versions/v286/native_manifest.json').read_bytes()).hexdigest(),
        claim='Measured body poses; geometric hard support and soft atlas kept separate. Free-only margins never replace refused-pose counts.')
    destination = results / 'physical_support_summary.json'
    if destination.exists():
        assert json.loads(destination.read_text()) == report
    else:
        with destination.open('x') as output:
            json.dump(report, output, indent=2)
            output.write('\n')
    print(json.dumps(dict(case_id=case, samples=len(rows))), flush=True)


if __name__ == '__main__':
    import sys
    audit(sys.argv[1])
