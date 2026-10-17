"""Package the pinned Building inputs once; no ROS, simulator or planning run."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

VERSION = Path(__file__).resolve().parents[1]
BASE = VERSION.parents[1]
sys.path.insert(0, str(VERSION / 'src/lite3_nav2_bridge'))
from lite3_nav2_bridge.terrain_bundle import TerrainBundle, TOPICS, fnv64


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def export(output, physical_floor, route_map, support_gap):
    output = Path(output)
    if output.exists():
        raise ValueError('Use a new terrain package directory')
    floor_info = json.loads((VERSION.parent/'v196/physical_floor_input.json').read_text())
    route_info = json.loads((VERSION.parent/'v196/global_map_input.json').read_text())
    gap_info = json.loads((VERSION.parent/'v196/support_coverage_input.json').read_text())
    for path, digest in [(physical_floor, floor_info['files']['physical_floor.f32']['sha256']),
                         (route_map, route_info['map_sha256']), (support_gap, gap_info['sha256'])]:
        if sha(path) != digest:
            raise ValueError('Pinned Building input mismatch: ' + str(path))
    core_path = BASE/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_core.py'
    if sha(core_path) != floor_info['producer']['sha256']:
        raise ValueError('Pinned terrain producer changed')
    core = module('v203_legacy_ground', core_path)
    exporter_path = VERSION.parent/'v201/tools/export_pct_map.py'
    expected = json.loads((VERSION.parent/'v201/manifest.json').read_text())['source_files']['tools/export_pct_map.py']
    if sha(exporter_path) != expected:
        raise ValueError('Pinned native map exporter changed')
    exporter = module('v203_legacy_pct_export', exporter_path)
    source = core.load_pinned_map(BASE/'inputs/new_building.pickle')
    elevation = core.load_paired_elevations(BASE/'inputs/new_building_original_precision.npz', source)
    navigation = core.selected_ground_points(source, paired_elevations=elevation).astype('<f4').tobytes()
    surface = core.load_dense_surface_points(BASE/'inputs/new_building_dense_surface.npy').astype('<f4').tobytes()
    payloads = {'navigation': navigation, 'surface': surface, 'physical_floor': Path(physical_floor).read_bytes()}
    assert hashlib.sha256(navigation).hexdigest() == floor_info['navigation_payload_sha256']
    assert hashlib.sha256(surface).hexdigest() == floor_info['selected_surface_payload_sha256']
    output.mkdir(parents=True)
    exporter.export_map(route_map, output/'route.pct')
    shutil.copyfile(support_gap, output/'support_gap.txt')
    def entry(path):
        return {'file': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path)}
    clouds = {}
    for role, data in payloads.items():
        path = output/(role+'.f32'); path.write_bytes(data)
        prefix = 'pct_physical_floor' if role == 'physical_floor' else 'pct_tomogram'
        clouds[role] = dict(entry(path), role=role, topic=TOPICS[role], points=len(data)//16,
                            source_id=prefix+'/fnv64/'+fnv64(data))
    result = {'format': 'LITE3_TERRAIN_V1', 'frame': 'world', 'resolution': 0.1, 'z_offset': 0.03,
              'physical_origin': [floor_info['physical_origin_x_m'], floor_info['physical_origin_y_m']],
              'pct': dict(entry(output/'route.pct'), source_sha256=sha(route_map)),
              'clouds': clouds,
              'support_gap': dict(entry(output/'support_gap.txt'), fnv64=gap_info['fnv64'], negative_only=True),
              'provenance': {'navigation_source': core.MAP_SHA, 'elevations': core.ELEVATION_SOURCE_SHA,
                             'surface_source': core.DENSE_SURFACE_SHA, 'physical_floor': sha(physical_floor),
                             'legacy_producer': sha(core_path), 'native_exporter': sha(exporter_path)}}
    target = output/'terrain.json'; target.write_text(json.dumps(result, indent=2)+'\n')
    checked = TerrainBundle(target); checked.load_clouds(); checked.native_parameters()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--physical-floor', type=Path, required=True)
    parser.add_argument('--route-map', type=Path, required=True)
    parser.add_argument('--support-gap', type=Path, required=True)
    args = parser.parse_args()
    result = export(args.output, args.physical_floor, args.route_map, args.support_gap)
    print(json.dumps({'terrain_manifest': str(args.output/'terrain.json'),
                      'point_counts': {k:v['points'] for k,v in result['clouds'].items()}}))
