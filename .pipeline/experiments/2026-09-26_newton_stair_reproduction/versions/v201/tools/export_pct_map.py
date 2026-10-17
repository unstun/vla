"""One-time export of a trusted, pinned tomogram to PCT's native input matrices."""
import argparse
import hashlib
import json
from pathlib import Path
import pickle
import struct

import numpy as np


def export_map(source, destination):
    source, destination = Path(source), Path(destination)
    with source.open('rb') as stream:
        data = pickle.load(stream)
    tomo = np.asarray(data['data'], dtype=np.float32)
    if tomo.ndim != 4 or tomo.shape[0] != 5 or min(tomo.shape[1:]) < 1:
        raise ValueError('Expected five tomogram channels with nonempty layer/X/Y axes')
    resolution = float(data['resolution'])
    center = np.asarray(data['center'], dtype=np.float64)
    h0, dh = float(data['slice_h0']), float(data['slice_dh'])
    if resolution <= 0 or dh <= 0 or center.shape != (2,) or not np.isfinite([resolution, *center, h0, dh]).all():
        raise ValueError('Invalid map geometry')
    trav, gx, gy, raw_ground, ceiling = tomo
    valid = np.isfinite(raw_ground)
    ground = np.nan_to_num(raw_ground, nan=-100)
    ceiling = np.nan_to_num(ceiling, nan=1e6)
    # Exactly the existing TomogramPlanner.initPlanner preprocessing, in float32.
    delta_cost = trav[1:] - trav[:-1]
    delta_height = np.abs(ground[1:] - ground[:-1])
    up, down = np.zeros_like(trav, dtype=bool), np.zeros_like(trav, dtype=bool)
    up[:-1] = (delta_cost < -8.) & (delta_height < .1) & ~np.isnan(ground[1:])
    down[1:] = (delta_cost > 8.) & (delta_height < .1) & ~np.isnan(ground[:-1])
    gateway = np.zeros_like(trav, dtype=np.int32)
    gateway[up], gateway[down] = 2, -2
    matrices = (trav, ground, ceiling, gateway, gy, -gx)
    if not all(np.isfinite(matrix).all() for matrix in matrices):
        raise ValueError('Nonfinite native map input')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(struct.pack('<8sIII5d', b'PCTMAP01', *tomo.shape[1:], resolution, *center, h0, dh))
        for matrix in matrices:
            stream.write(np.asarray(matrix, dtype='<f8', order='C').tobytes())
        stream.write(valid.astype(np.uint8).tobytes(order='C'))
    receipt = {'format': 'PCTMAP01', 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
               'bundle_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
               'bundle_bytes': destination.stat().st_size, 'dimensions_layer_x_y': list(tomo.shape[1:]),
               'resolution': resolution, 'center': center.tolist(), 'slice_h0': h0, 'slice_dh': dh,
               'native_matrix_order': ['cost', 'ground', 'ceiling', 'gateway', 'grad_y', 'negative_grad_x'],
               'ground_validity_mask': 'original float32 ground isfinite; not inferred from the -100 fill'}
    destination.with_suffix(destination.suffix + '.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(json.dumps(export_map(args.source, args.destination)))
