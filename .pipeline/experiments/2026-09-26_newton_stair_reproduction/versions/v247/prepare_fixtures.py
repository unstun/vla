"""Restore native PCT costs; verify unchanged support/elevation source bytes."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

BASE = Path('/data/sun/vla_mppi_20261009')
HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parents[1]
WORK = BASE / 'physical_traversability_v247/native'
BUILDING = WORK / 'fixtures/building'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    sys.path.insert(0, str(EXPERIMENT / 'runtime_sources/bridge/lite3_sim_bridge'))
    from pct_sim_clock_core import load_pinned_map, load_paired_elevations, selected_ground_points
    source_path = EXPERIMENT / 'inputs/new_building.pickle'
    source = load_pinned_map(source_path)
    elevations = load_paired_elevations(EXPERIMENT / 'inputs/new_building_original_precision.npz', source)
    original_navigation = selected_ground_points(source, paired_elevations=elevations).astype('<f4').tobytes()
    # v135 is global-cost preprocessing. Do not silently change native selected
    # terrain, physical floors or the scorer while removing that preprocessing.
    assert (BUILDING / 'navigation.f32').read_bytes() == original_navigation
    spec = importlib.util.spec_from_file_location('native_export', HERE.parent / 'v201/tools/export_pct_map.py')
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    route = BUILDING / 'native_original.pct'
    if not route.exists():
        exporter.export_map(source_path, route)
    terrain_path = BUILDING / 'terrain.json'
    old = json.loads(terrain_path.read_text())
    new = dict(old)
    new['pct'] = dict(old['pct'], file=route.name, bytes=route.stat().st_size, sha256=sha(route))
    (BUILDING / 'terrain247.json').write_text(json.dumps(new, indent=2) + '\n')
    environment = json.loads((BUILDING / 'environment225.json').read_text())
    environment['terrain_manifest_sha256'] = sha(BUILDING / 'terrain247.json')
    environment['parent_manifest_sha256'] = sha(BUILDING / 'environment225.json')
    environment['binding_note'] = 'Only PCT cost/gateway preprocessing restored; native support clouds and ENV225 bytes unchanged.'
    (BUILDING / 'environment247.json').write_text(json.dumps(environment, indent=2) + '\n')
    report = dict(source_map_sha256=sha(source_path), route_sha256=sha(route),
                  original_navigation_byte_identical=True,
                  support_cloud_sha256={name: sha(BUILDING / (name + '.f32')) for name in ('navigation', 'surface', 'physical_floor')},
                  environment_sha256=sha(BUILDING / 'environment225.env'),
                  terrain_manifest_sha256=sha(BUILDING / 'terrain247.json'))
    (WORK / 'fixture_receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
