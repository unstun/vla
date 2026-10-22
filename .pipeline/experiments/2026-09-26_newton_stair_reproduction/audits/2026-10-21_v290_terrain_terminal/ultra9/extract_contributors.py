"""Recover actual measured ray endpoints in the refused contributor voxels."""
from pathlib import Path
import csv
import hashlib
import json
import sys
import numpy as np

R = Path('/home/ubuntu/sun/vla_v290_20261021')
P = Path('/home/ubuntu/sun/vla_v289_20261020')
sys.path.insert(0, str(P/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v196'))
from analyze_remote import Capture


def main():
    report = dict(physics_steps=0, cases=[])
    for case in ['A04', 'G05', 'CU06', 'CM02']:
        raw = P/f'physical_runs/v289_{case}_attempt01/runs/v289_{case}_attempt01'
        capture = Capture(raw)
        contributors = list(csv.DictReader((R/f'captured_results/candidate/{case}/contributors.csv').open()))
        cells = set(tuple(np.floor(np.array([float(x[k]) for k in ['x','y','z']])/.05+1e-6).astype(int))
            for x in contributors if x['terrain']=='0' or x['current_nonterrain']=='1' or x['historical_nonterrain']=='1')
        samples = []
        cell_keys = np.ascontiguousarray(sorted(cells),dtype=np.int64).view(np.dtype((np.void,24))).ravel()
        for sensor in capture.rows('sensor.jsonl'):
            points = np.load(raw/sensor['file'])['world_points']
            ids=np.ascontiguousarray(np.floor(points/.05+1e-6),dtype=np.int64)
            keys=ids.view(np.dtype((np.void,24))).ravel()
            for p in points[np.isin(keys,cell_keys)]:
                samples.append([sensor['sim_time_s'], *map(float,p)])
        path = R/f'captured/{case}/contributor_points.txt'
        path.write_text(''.join(' '.join(map(str,x))+'\n' for x in samples))
        report['cases'].append(dict(case_id=case, cells=len(cells), measured_points=len(samples),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(), contributor_csv_sha256=hashlib.sha256(
                (R/f'captured_results/candidate/{case}/contributors.csv').read_bytes()).hexdigest()))
        print(case,len(cells),len(samples),flush=True)
    (R/'evidence/contributor_inputs01.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    main()
