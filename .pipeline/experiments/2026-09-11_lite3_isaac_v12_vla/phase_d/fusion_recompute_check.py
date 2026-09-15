"""Phase D.0f: prove from a finished run that the model received the fused image, and that the fusion is reproducible.

Runs in the same container image as the Isaac server (same numpy and cv2), after the episode:

    /isaac-sim/python.sh phase_d/fusion_recompute_check.py --run-dir RUN_DIR --tools-dir TOOLS_DIR

Checks, written to RUN_DIR/fusion_recompute_check.json:
1. recompute: for every decision image the server saved losslessly (head and D435i PNG, D435i depth .npy, ideal PNG),
   the pinned fusion with the run's own recorded config reproduces the saved fused image and coverage bit for bit;
2. override: every saved fused image differs from the ideal render saved with it;
3. delivery: the client's first decision frame is closer to the fused image than to the ideal render (the client saves
   it as JPEG, so equality is not expected), over the whole image and over the pixels the fusion leaves uncovered.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent


def load_rgb(path):
    return np.asarray(Image.open(path).convert('RGB'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--tools-dir', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(HERE))
    import isaac_fusion

    record = json.loads((args.run_dir / 'isaac' / 'isaac_episode.json').read_text())
    config = record['fusion']['config']
    fusion = isaac_fusion.IsaacFusion(config, isaac_fusion.virtual_spec(config, record['episode']['camera']),
                                      args.tools_dir)
    fusion_dir = args.run_dir / 'isaac' / 'fusion'
    frames = []
    for fused_path in sorted(fusion_dir.glob('image_*_fused.png')):
        stem = str(fused_path)[:-len('_fused.png')]
        saved_fused = load_rgb(fused_path)
        saved_cov = np.asarray(Image.open(stem + '_coverage.png'))
        ideal = load_rgb(stem + '_ideal.png')
        fused, cov, row = fusion.fuse(load_rgb(stem + '_head.png'), load_rgb(stem + '_d435.png'),
                                      np.load(stem + '_d435_depth_m.npy'), ideal)
        frames.append({
            'image': Path(stem).name,
            'fused_bit_identical': bool(np.array_equal(fused, saved_fused)),
            'coverage_bit_identical': bool(np.array_equal(cov, saved_cov)),
            'max_abs_pixel_diff': int(np.abs(fused.astype(np.int16) - saved_fused.astype(np.int16)).max()),
            'fused_differs_from_ideal_fraction': float((saved_fused != ideal).any(axis=2).mean()),
            'coverage': row['coverage'],
        })

    delivery = None
    client_first = args.run_dir / 'client' / 'decision_frames' / 'decision_0001.jpg'
    first_stem = fusion_dir / 'image_0001'
    if client_first.exists() and Path(str(first_stem) + '_fused.png').exists():
        client = load_rgb(client_first).astype(np.float64)
        fused = load_rgb(str(first_stem) + '_fused.png').astype(np.float64)
        ideal = load_rgb(str(first_stem) + '_ideal.png').astype(np.float64)
        uncovered = np.asarray(Image.open(str(first_stem) + '_coverage.png')) == 0

        def mae(a, b, mask=None):
            err = np.abs(a - b).mean(axis=2)
            return float(err[mask].mean()) if mask is not None and mask.any() else (
                float(err.mean()) if mask is None else None)
        delivery = {
            'client_frame': str(client_first.relative_to(args.run_dir)),
            'mae_client_vs_fused': mae(client, fused), 'mae_client_vs_ideal': mae(client, ideal),
            'uncovered_pixels': int(uncovered.sum()),
            'mae_client_vs_fused_uncovered': mae(client, fused, uncovered),
            'mae_client_vs_ideal_uncovered': mae(client, ideal, uncovered),
        }
        delivery['client_received_fused'] = (
            delivery['mae_client_vs_fused'] < delivery['mae_client_vs_ideal']
            and (delivery['mae_client_vs_fused_uncovered'] is None
                 or delivery['mae_client_vs_fused_uncovered'] < delivery['mae_client_vs_ideal_uncovered']))

    checks = {
        'saved_frames_present': bool(frames),
        'all_fused_bit_identical': bool(frames) and all(f['fused_bit_identical'] for f in frames),
        'all_coverage_bit_identical': bool(frames) and all(f['coverage_bit_identical'] for f in frames),
        'all_fused_differ_from_ideal': bool(frames) and all(f['fused_differs_from_ideal_fraction'] > 0 for f in frames),
        'client_received_fused': bool(delivery and delivery['client_received_fused']),
    }
    result = {'run': args.run_dir.name, 'fused_camera_sha256': fusion.module_sha256,
              'cv2_available': fusion.fc.cv2 is not None, 'frames': frames, 'delivery': delivery,
              'checks': checks, 'passed': all(checks.values())}
    (args.run_dir / 'fusion_recompute_check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'checks': checks, 'delivery': delivery}, indent=1))
    print('FUSION_RECOMPUTE_CHECK', 'PASSED' if result['passed'] else 'FAILED')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
