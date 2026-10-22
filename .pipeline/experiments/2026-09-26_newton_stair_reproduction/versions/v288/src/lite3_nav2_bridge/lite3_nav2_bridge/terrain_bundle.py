"""One manifest for distinct static navigation, surface and physical-floor roles."""
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np

TOPICS = {'navigation': '/pct_tomogram', 'surface': '/pct_ground_surface',
          'physical_floor': '/pct_physical_floor'}
FIELDS = (('x', 0, 7, 1), ('y', 4, 7, 1), ('z', 8, 7, 1), ('intensity', 12, 7, 1))


def fnv64(data):
    value = 14695981039346656037
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & 0xffffffffffffffff
    return str(value)


class TerrainBundle:
    """Read metadata once; load cloud bytes once in the sole static publisher."""
    def __init__(self, manifest):
        self.path = Path(manifest).resolve(strict=True)
        self.metadata = json.loads(self.path.read_text())
        m = self.metadata
        if m.get('format') != 'LITE3_TERRAIN_V1' or m.get('frame') != 'world':
            raise ValueError('Unsupported static terrain format/frame')
        if set(m['clouds']) != set(TOPICS) or m['support_gap'].get('negative_only') is not True:
            raise ValueError('Static terrain roles must remain distinct')
        if not math.isfinite(m['resolution']) or m['resolution'] <= 0 or \
                not all(math.isfinite(x) for x in [*m['physical_origin'], m['z_offset']]) or \
                len(m['physical_origin']) != 2:
            raise ValueError('Invalid static terrain geometry')
        for role, topic in TOPICS.items():
            entry = m['clouds'][role]
            if entry['topic'] != topic or entry['role'] != role or entry['points'] <= 0 or \
                    entry['bytes'] != entry['points'] * 16:
                raise ValueError('Invalid static cloud role/layout: ' + role)
            self.file(entry)
        self.file(m['pct']); self.file(m['support_gap'])
        self._clouds = None

    def file(self, entry):
        return (self.path.parent / entry['file']).resolve(strict=True)

    def checked_bytes(self, entry):
        data = self.file(entry).read_bytes()
        if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('Static terrain identity mismatch: ' + entry['file'])
        return data

    def load_clouds(self):
        if self._clouds is None:
            clouds = {}
            for role, entry in self.metadata['clouds'].items():
                data = self.checked_bytes(entry)
                if not np.isfinite(np.frombuffer(data, dtype='<f4')).all():
                    raise ValueError('Nonfinite static cloud: ' + role)
                prefix = 'pct_physical_floor' if role == 'physical_floor' else 'pct_tomogram'
                if entry['source_id'] != prefix + '/fnv64/' + fnv64(data):
                    raise ValueError('Static cloud source ID mismatch: ' + role)
                clouds[role] = data
            self._clouds = clouds
        return self._clouds

    def native_parameters(self):
        m = self.metadata
        pct = self.checked_bytes(m['pct'])
        if len(pct) < 60:
            raise ValueError('Truncated PCT lattice header')
        magic, layers, nx, ny, resolution, cx, cy, h0, dh = struct.unpack_from('<8sIII5d', pct)
        if magic != b'PCTMAP01' or min(layers, nx, ny) <= 0 or \
                len(pct) != 60 + 49 * layers * nx * ny or \
                not all(math.isfinite(v) for v in (resolution, cx, cy, h0, dh)) or \
                resolution != m['resolution'] or dh <= 0:
            raise ValueError('Invalid PCT lattice header')
        origin_x = cx - (nx // 2 + 0.5) * resolution
        origin_y = cy - (ny // 2 + 0.5) * resolution
        gap = self.checked_bytes(m['support_gap'])
        if fnv64(gap) != m['support_gap']['fnv64']:
            raise ValueError('Static support mask identity mismatch')
        return {
            'grid_map.support_lattice_enabled': True,
            'grid_map.support_lattice_origin_x': origin_x,
            'grid_map.support_lattice_origin_y': origin_y,
            'grid_map.support_gap_path': str(self.file(m['support_gap'])),
            'grid_map.support_gap_fnv64': m['support_gap']['fnv64'],
            'grid_map.reactive_surface_ground_topic': TOPICS['surface'],
            'grid_map.reactive_physical_floor_topic': TOPICS['physical_floor'],
            'grid_map.physical_floor_source_id': m['clouds']['physical_floor']['source_id'],
            'grid_map.physical_floor_surface_source_id': m['clouds']['surface']['source_id'],
            'grid_map.physical_floor_navigation_source_id': m['clouds']['navigation']['source_id'],
            'grid_map.physical_floor_origin_x': m['physical_origin'][0],
            'grid_map.physical_floor_origin_y': m['physical_origin'][1],
            'grid_map.physical_floor_resolution': m['resolution'],
            'grid_map.reactive_tomogram_resolution': m['resolution'],
            'grid_map.reactive_tomogram_z_offset': m['z_offset'],
        }


class ClockGate:
    """Unchanged two-advancing-positive-samples gate, rearmed by clock reset."""
    def __init__(self):
        self._first_positive_ns = None
        self._last_ns = None
        self._published = False

    def observe(self, clock_ns):
        if clock_ns <= 0:
            if self._last_ns is not None and clock_ns < self._last_ns:
                self._first_positive_ns = None
                self._published = False
            self._last_ns = clock_ns
            return None
        if self._last_ns is not None and clock_ns < self._last_ns:
            self._first_positive_ns = None
            self._published = False
        self._last_ns = clock_ns
        if self._first_positive_ns is None:
            self._first_positive_ns = clock_ns
            return None
        if self._published or clock_ns <= self._first_positive_ns:
            return None
        self._published = True
        return clock_ns
