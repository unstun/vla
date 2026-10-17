"""Old Python-wrapper semantics versus the direct C++ adapter, on fixed inputs."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import struct
from unittest.mock import patch

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--native-probe', type=Path, required=True)
    parser.add_argument('--legacy-python', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.legacy_python))
    from pct_planner.config import Config
    from pct_planner.planner_wrapper import TomogramPlanner
    import pct_planner.planner_wrapper as wrapper
    matrix_checks = []
    for name in ('flat', 'building'):
        source = (args.fixtures / 'flat.pickle' if name == 'flat' else
                  Path((args.fixtures / 'building_source.txt').read_text().strip()))
        captured = []
        class NativeMapCapture:
            def __init__(self, **kwargs):
                pass
            def init_map(self, *values):
                captured.extend(values)
        with patch.object(wrapper.ele_planner, 'OfflineElePlanner', NativeMapCapture):
            original = TomogramPlanner(Config(), str(args.fixtures))
            original.loadTomogram(tomogram_path=str(source))
        data = (args.fixtures / (name + '.pct')).read_bytes()
        magic, layers, nx, ny, resolution, cx, cy, h0, dh = struct.unpack('<8sIII5d', data[:60])
        assert magic == b'PCTMAP01'
        assert (layers, nx, ny) == (original.n_slice, *original.map_dim)
        assert (resolution, cx, cy, h0, dh) == (original.resolution, *original.center, original.slice_h0, original.slice_dh)
        count, offset = layers * nx * ny, 60
        for expected_matrix in captured[5:]:
            actual_matrix = np.frombuffer(data, dtype='<f8', count=count, offset=offset).reshape(layers * nx, ny)
            assert np.array_equal(actual_matrix, expected_matrix), name
            offset += count * 8
        assert np.array_equal(np.frombuffer(data[offset:], dtype=np.uint8).reshape(layers, nx, ny), original.elev_g_valid)
        matrix_checks.append({'map': name, 'six_native_matrices_exact': True, 'original_validity_mask_exact': True})
    rows = []
    for case in json.loads((args.fixtures / 'cases.json').read_text()):
        cfg = copy.deepcopy(Config())
        cfg.planner = copy.deepcopy(cfg.planner)
        cfg.planner.use_quintic = case.get('quintic', True)
        reference = case.get('reference_height', .35)
        source = (args.fixtures / (case['map'] + '.pickle') if case['map'] != 'building' else
                  Path((args.fixtures / 'building_source.txt').read_text().strip()))
        legacy = TomogramPlanner(cfg, str(args.fixtures))
        legacy.loadTomogram(tomogram_path=str(source))
        legacy.planner.set_reference_height(reference)
        first = last = expected = None
        try:
            first, last = legacy.pose2idx(case['start']), legacy.pose2idx(case['goal'])
            expected = legacy.plan(case['start'], case['goal'], optimize=True)
            if expected is not None:
                optimizer = (legacy.planner.get_trajectory_optimizer_wnoj() if cfg.planner.use_quintic else
                             legacy.planner.get_trajectory_optimizer())
                expected = np.array(expected, copy=True)
                # Exactly the old MissionBridge output, not the wrapper's +0.5 m.
                expected[:, 2] = np.asarray(optimizer.get_heights()).reshape(-1)
        except ValueError:
            expected = None
        output = args.fixtures / (case['name'] + '.cpp.txt')
        command = [str(args.native_probe), str(args.fixtures / (case['map'] + '.pct')),
                   str(reference), str(int(cfg.planner.use_quintic)),
                   *map(str, case['start']), *map(str, case['goal']), str(output)]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        (args.fixtures / (case['name'] + '.native.log')).write_text(result.stdout)
        lines = output.read_text().splitlines()
        row = dict(case, cpp_returncode=result.returncode, legacy_accepted=expected is not None)
        if first is not None and last is not None:
            assert np.array_equal(np.fromstring(lines[0], sep=' ', dtype=int), first), case['name']
            assert np.array_equal(np.fromstring(lines[1], sep=' ', dtype=int), last), case['name']
            row.update(start_index=first.tolist(), goal_index=last.tolist())
        if expected is None:
            assert result.returncode == 2 and any(line.startswith('ERROR ') for line in lines), case['name']
            row['points'] = 0
        else:
            assert result.returncode == 0, (case['name'], result.stdout)
            actual = np.array([np.fromstring(line, sep=' ') for line in lines[2:]])
            assert actual.shape == expected.shape, (case['name'], actual.shape, expected.shape)
            error = float(np.max(np.abs(actual - expected)))
            assert error <= 1e-6, (case['name'], error)
            row.update(points=len(actual), max_abs_xyz_error_m=error,
                       first_point=actual[0].tolist(), last_point=actual[-1].tolist(),
                       reference_output_sha256=hashlib.sha256(expected.tobytes()).hexdigest())
        rows.append(row)
    loaded = sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines()
                     if 'libele_planner_lib.so' in line or 'libgpmp_optimizer.so' in line})
    report = {'passed': True, 'cases': rows, 'map_preprocessing': matrix_checks, 'tolerance_m': 1e-6,
              'legacy_wrapper': wrapper.__file__, 'legacy_native_loaded': loaded,
              'legacy_wrapper_sha256': hashlib.sha256(Path(wrapper.__file__).read_bytes()).hexdigest(),
              'physics_steps': 0, 'navigation_goals': 0}
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': True, 'cases': len(rows), 'accepted': sum(r['points'] > 0 for r in rows)}))


if __name__ == '__main__':
    main()
