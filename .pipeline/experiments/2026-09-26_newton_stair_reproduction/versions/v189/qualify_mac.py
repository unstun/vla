"""Write complete pre-freeze Mac quality from actual build, host and graph evidence."""
from pathlib import Path
import argparse
import json
import shutil
from native_gate import sha, validate_quality
from run_mac_full import HERE, validate_task


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-root', type=Path, required=True)
    args = parser.parse_args()
    task = validate_task(args.task_root)
    evidence = task / 'evidence'
    receipt = json.loads((evidence / 'v189_native_receipt.json').read_text())
    host = json.loads((evidence / 'v189_host_tests.json').read_text())
    graph = json.loads((evidence / 'v189_native_graph_preflight.json').read_text())
    loaded = json.loads((evidence / 'v189_overlay_loaded.json').read_text())
    assert receipt['passed'] and receipt['native_version'] == 'v189'
    assert host['passed'] and host['host'] == 'Darwin/arm64'
    assert host['errors'] == host['failures'] == host['skipped'] == 0
    assert graph['passed'] and not graph['physics_advanced'] and loaded['passed']
    assert graph['generated_finish_dist_m'] == 0.02
    assert graph['route_lookahead_heading_enabled'] is True and graph['route_lookahead_dist'] == 0.5
    assert all(row['libraries'] == ['/task/recovery_v189/install/scan_nav2_controller/lib/libscan_nav2_controller.so']
               for row in loaded['processes'])
    tests = receipt['tests']
    quality = dict(passed=True, native_version='v189', execution_platform=receipt['platform'],
        native_packages_available=receipt['native_packages_available'], rebuilt_packages=2,
        native_colcon_summary=tests['colcon_summary'],
        unique_controller_gtest_cases=tests['unique_gtest_cases'],
        controller_gtest_cases=tests['controller_gtest_cases'],
        gtest_count_scope='44 controller + 1 tracking parity + 1 executor shutdown; 49 colcon entries include 3 CTest wrappers',
        native_terminal_regressions=tests['terminal_markers'] == ['V176_TERMINAL_CAPTURE_PASS', 'V189_CORNER_LOOKAHEAD_PASS'],
        generated_profile_cases=tests['generated_profile_cases'], host_tests=host['tests'],
        runtime_receipts={'candidate': sha(evidence / 'v189_native_receipt.json')},
        actual_graph_verified=True, native_graph_preflight_sha256=sha(evidence / 'v189_native_graph_preflight.json'),
        overlay_loaded_sha256=sha(evidence / 'v189_overlay_loaded.json'),
        host_test_results_sha256=sha(evidence / 'v189_host_tests.json'),
        full_navigation_accepted=False,
        claim='Component and live graph qualification for Mac ARM64 only; full-route results are appended separately.')
    validate_quality(quality)
    output = HERE / 'verification'
    output.mkdir(exist_ok=False)
    paths = [evidence / name for name in [
        'v189_native_receipt.json', 'v189_native_build.log', 'v189_build_request.json',
        'v189_native_graph_preflight.json', 'v189_overlay_loaded.json',
        'v189_graph_preflight.log', 'v189_host_tests.json', 'v189_host_tests.log',
        'v189_native_extra_tests.log']]
    paths += sorted((task / 'recovery_v189/build/scan_nav2_controller/test_results/scan_nav2_controller').glob('*.gtest.xml'))
    for path in paths:
        shutil.copyfile(path, output / path.name)
    shutil.copyfile(task / 'restore_archives/local_manifest.json', output / 'environment_archives.json')
    shutil.copyfile(task / 'restore_archives/remote_sha256.txt', output / 'environment_remote_sha256.txt')
    shutil.copyfile(task / 'recovery_v189/source_identity.json', output / 'native_source_identity.json')
    quality['evidence_files'] = {str(path.relative_to(HERE)): sha(path) for path in sorted(output.iterdir())}
    with (HERE / 'quality.json').open('x') as stream:
        stream.write(json.dumps(quality, indent=2) + '\n')
    print(json.dumps({'passed': True, 'host_tests': host['tests'], 'quality_sha256': sha(HERE / 'quality.json')}))


if __name__ == '__main__':
    main()
