"""Invoke pinned fixture producers with only their host output roots rebound."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import shutil
import sys

HERE = Path(__file__).resolve().parent
VERSIONS = HERE.parent
BASE = VERSIONS.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['floor_coverage', 'global_terrain'])
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    if args.stage == 'floor_coverage':
        output = args.prefix / 'fixed_curve_input/physical_floor.f32'
        sys.argv = [str(VERSIONS / 'v187/derive_mac_floor.py'), '--output', str(output)]
        runpy.run_path(sys.argv[0], run_name='__main__')
        coverage = module('v234_coverage', VERSIONS / 'v134/generate_coverage.py')
        coverage.TASK = args.prefix
        coverage.main()
        expected = json.loads((VERSIONS / 'v196/support_coverage_input.json').read_text())
        assert sha(args.prefix / 'support_coverage_v134/partial.txt') == expected['sha256']
    else:
        global_map = module('v234_global_coverage', VERSIONS / 'v135/prepare_global.py')
        global_map.TASK = args.prefix
        global_map.main()
        route = args.prefix / 'global_coverage_v135_foxy/map.pickle'
        expected = json.loads((VERSIONS / 'v196/global_map_input.json').read_text())
        assert sha(route) == expected['map_sha256']
        fixture_reference = VERSIONS / 'v225/results/fixtures'
        fixtures = args.work / 'fixtures'
        assert not fixtures.exists()
        shutil.copytree(fixture_reference, fixtures)
        expected_terrain = (fixtures / 'building/terrain.json').read_bytes()
        # Only small archived JSON manifests exist here; preserve them separately.
        shutil.move(str(fixtures / 'building'), str(fixtures / 'building_reference'))
        export = module('v234_terrain_export', VERSIONS / 'v203/tools/export_terrain_bundle.py')
        export.export(fixtures / 'building', args.prefix / 'fixed_curve_input/physical_floor.f32',
                      route, args.prefix / 'support_coverage_v134/partial.txt')
        assert (fixtures / 'building/terrain.json').read_bytes() == expected_terrain
        for item in (fixtures / 'building_reference').iterdir():
            if not (fixtures / 'building' / item.name).exists():
                shutil.copyfile(item, fixtures / 'building' / item.name)
        sys.path.insert(0, str(VERSIONS / 'v201/tools'))
        make = module('v234_fixed_maps', VERSIONS / 'v201/tools/make_fixed_inputs.py')
        make.make(fixtures, route)
    evidence = args.prefix / 'evidence'
    evidence.mkdir(exist_ok=True)
    report = dict(passed=True, actual_execution_host='gpu40901', physics_steps=0,
                  stage=args.stage, producers='Pinned v187/v134/v135/v203/v201, host output roots only',
                  helper_floor_provenance_host_literal='gpu5070ti (inherited; actual host is gpu40901)')
    (evidence / (args.stage + '.json')).write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
