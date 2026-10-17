"""Write complete pre-freeze Mac v194 Option B quality from actual build, host and graph evidence."""
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
    if (HERE / 'manifest.json').exists():
        raise ValueError('Never rewrite frozen qualification')
    task = validate_task(args.task_root)
    evidence = task / 'evidence'
    receipt = json.loads((evidence / 'v194_native_receipt.json').read_text())
    host = json.loads((evidence / 'v194_host_tests.json').read_text())
    graph = json.loads((evidence / 'v194_native_graph_preflight.json').read_text())
    loaded = json.loads((evidence / 'v194_overlay_loaded.json').read_text())
    protected = json.loads((evidence / 'v194_protected_comparison.json').read_text())
    assert protected['passed'] and all(row['passed'] for row in protected['paths'].values())
    assert protected['baseline_sha256'] == sha(evidence / 'v194_protected_before.json')
    assert receipt['passed'] and receipt['native_version'] == 'v194'
    assert host['passed'] and host['host'] == 'Darwin/arm64'
    assert host['errors'] == host['failures'] == host['skipped'] == 0
    assert graph['passed'] and not graph['physics_advanced'] and loaded['passed']
    assert graph['applied_transport'] == 'shared' and graph['shared_mount_bidirectional_verified']
    assert protected['native_source_matches_inventory'] and protected['native_build_reused'] is False
    assert graph['generated_finish_dist_m'] == 0.02
    assert graph['route_lookahead_heading_enabled'] is True and graph['route_lookahead_dist'] == 0.5
    assert graph['navigation_goal_sent'] is False
    assert graph['recovery_wait_duration_s'] == 1 and graph['stock_recovery_retries'] == 6
    assert graph['scan_execution'] == loaded['scan_execution'] == 'embedded_native_worker'
    expected_states = {name: 'active' for name in (
        '/controller_server', '/planner_server', '/recoveries_server', '/nav2_internal/bt_navigator')}
    assert graph['lifecycle_states'] == loaded['lifecycle_states'] == expected_states
    assert loaded['processes'] and not loaded['scan_processes']
    assert all(row['libraries'] == ['/task/recovery_v194/install/scan_nav2_controller/lib/libscan_nav2_controller.so']
               for row in loaded['processes'])
    assert all(row['native_libraries'] == ['/task/recovery_v194/install/scan_planner/lib/libscan_native_core.so']
               for row in loaded['processes'])
    tests = receipt['tests']
    quality = dict(passed=True, integration_version='v194', native_build_reused=False, parent='v193', navigation_parent='v192', native_binary_underlay='v176', native_version='v194', execution_platform=receipt['platform'],
        recovery_wait_duration_s=1, stock_recovery_retries=6, canonical_goal_pose_locked=True,
        control_yaw_tolerance_scale=0.5, cached_path_replay_enabled=False,
        native_packages_available=receipt['native_packages_available'], rebuilt_packages=11,
        native_colcon_summary=tests['colcon_summary'],
        unique_controller_gtest_cases=tests['unique_gtest_cases'],
        controller_gtest_cases=tests['controller_gtest_cases'],
        gtest_count_scope='20 controller + 1 tracking parity + 1 executor shutdown + 8 lite3_nav2_plugins + 9 lite3_nav2_bridge pytest; 45 colcon entries include CTest wrappers',
        native_terminal_regressions=tests['terminal_markers'] == ['V176_TERMINAL_CAPTURE_PASS', 'V194_CORNER_LOOKAHEAD_PASS'],
        generated_profile_cases=tests['generated_profile_cases'], host_tests=host['tests'],
        runtime_receipts={'candidate': sha(evidence / 'v194_native_receipt.json')},
        actual_graph_verified=True, native_graph_preflight_sha256=sha(evidence / 'v194_native_graph_preflight.json'),
        graph_lifecycle_states=expected_states, graph_synthetic_fixture=graph['synthetic_fixture'],
        physics_advanced=False, navigation_goal_sent=False, scan_execution=graph['scan_execution'],
        overlay_loaded_sha256=sha(evidence / 'v194_overlay_loaded.json'),
        host_test_results_sha256=sha(evidence / 'v194_host_tests.json'),
        full_navigation_accepted=False,
        claim='Component and live graph qualification for Mac ARM64 Option B direct Nav2+SCAN; full-route results are appended separately.')
    validate_quality(quality)
    output = HERE / 'verification'
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(exist_ok=False)
    paths = [evidence / name for name in [
        'v194_native_receipt.json', 'v194_native_build.log', 'v194_build_request.json',
        'v194_native_graph_preflight.json', 'v194_overlay_loaded.json',
        'v194_graph_preflight.log',
        'v194_host_tests.json', 'v194_host_tests.log',
        'v194_protected_before.json', 'v194_protected_comparison.json']]
    paths += sorted((task / 'recovery_v194/build/scan_nav2_controller/test_results/scan_nav2_controller').glob('*.gtest.xml'))
    for path in paths:
        shutil.copyfile(path, output / path.name)
    failed = evidence / 'v194_attempt01_failed'
    for path in sorted(failed.iterdir()):
        if path.is_file():
            shutil.copyfile(path, output / ('attempt01_failed_' + path.name))
    graph_root = Path(graph['graph_root'])
    for name in ('nav2.log', 'native_commands.json', 'nav2_params.yaml', 'nav2_params.bt.xml',
                 'selected_route_map.json', 'backend_config.json', 'backend_latest.json',
                 'inspect_overlay.py', 'preflight_tf.log'):
        shutil.copyfile(graph_root / name, output / ('graph_' + name))
    shutil.copyfile(task / 'restore_archives/local_manifest.json', output / 'environment_archives.json')
    shutil.copyfile(task / 'restore_archives/remote_sha256.txt', output / 'environment_remote_sha256.txt')
    shutil.copyfile(task / 'recovery_v194/source_identity.json', output / 'native_source_identity.json')
    quality['evidence_files'] = {str(path.relative_to(HERE)): sha(path) for path in sorted(output.iterdir())}
    (HERE / 'quality.json').write_text(json.dumps(quality, indent=2) + '\n')
    print(json.dumps({'passed': True, 'host_tests': host['tests'], 'quality_sha256': sha(HERE / 'quality.json')}))


if __name__ == '__main__':
    main()
