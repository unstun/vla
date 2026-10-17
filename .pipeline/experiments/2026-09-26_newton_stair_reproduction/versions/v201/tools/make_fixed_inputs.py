"""Create deterministic, regenerable map fixtures. Does not start navigation."""
import argparse
import json
from pathlib import Path
import pickle
import shutil

import numpy as np

from export_pct_map import export_map


def make(output, building):
    output.mkdir(parents=True, exist_ok=True)
    # Unequal dimensions and a displaced center expose unnoticed XY transposes.
    data = np.zeros((5, 2, 41, 31), dtype=np.float32)
    data[3, 0] = .15
    data[3, 1] = 1.5
    data[4] = 20.
    # Invalid ground cells exercise the original validity mask and fallback.
    data[3, :, 20, 15] = np.nan
    data[0, :, 0, :] = 100.
    data[0, :, -1, :] = 100.
    data[0, :, :, 0] = 100.
    data[0, :, :, -1] = 100.
    # Nonzero gradients are deliberately asymmetric, even on this flat fixture.
    data[1] = .02
    data[2] = -.03
    meta = dict(data=data, resolution=.125, center=np.array([2., -3.]), slice_h0=.15, slice_dh=1.35)
    with (output / 'flat.pickle').open('wb') as stream:
        pickle.dump(meta, stream, protocol=4)
    export_map(output / 'flat.pickle', output / 'flat.pct')
    # Reuse the restored coverage-constrained map, whose hash is recorded.
    export_map(building, output / 'building.pct')
    cases = [
        dict(name='flat_axes_lower', map='flat', start=[.5, -4., .5], goal=[3.5, -2., .5]),
        dict(name='flat_axes_upper', map='flat', start=[.5, -4., 1.85], goal=[3.5, -2., 1.85]),
        dict(name='flat_rounding_ties', map='flat', start=[.5625, -4.0625, .5], goal=[3.5625, -1.9375, .5]),
        dict(name='flat_non_quintic', map='flat', start=[.5, -4., .5], goal=[3.5, -2., .5], quintic=False),
        dict(name='flat_invalid_floor_fallback', map='flat', start=[2., -3., 1.55], goal=[3.5, -2., 1.85]),
        dict(name='flat_singleton', map='flat', start=[.5, -4., .5], goal=[.5, -4., .5]),
        dict(name='flat_outside', map='flat', start=[-100., -4., .5], goal=[3.5, -2., .5]),
        dict(name='building_reference_030', map='building', start=[-5.545314788818359, 6.01318883895874, .35804443359375], goal=[1.954685200623011, -2.9868112220934897, 4.833030509948731], reference_height=.3),
        dict(name='building_reference_035', map='building', start=[-5.545314788818359, 6.01318883895874, .40804443359375], goal=[1.954685200623011, -2.9868112220934897, 4.883030509948731]),
        dict(name='building_reverse', map='building', start=[1.954685200623011, -2.9868112220934897, 4.883030509948731], goal=[-5.545314788818359, 6.01318883895874, .40804443359375]),
        dict(name='building_recorded_singleton', map='building', start=[2.0688388347625732, -2.9184811115264893, 4.825720310211182], goal=[1.954685200623011, -2.9868112220934897, 4.833030509948731], reference_height=.3),
    ]
    (output / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    (output / 'building_source.txt').write_text(str(building) + '\n')
    return cases


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--building', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({'fixed_cases': len(make(args.output, args.building))}))
