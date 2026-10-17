"""Verify exact Mac v191 Option B native sources, installed overlays and re-executed test evidence."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import xml.etree.ElementTree as ET
from ament_index_python.packages import get_package_prefix

HERE = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image-id', required=True)
    args = parser.parse_args()
    assert platform.machine() == 'aarch64'
    task = Path('/task')
    workspace = task / 'recovery_v191'
    parent = task / 'evidence/v176_native_receipt.json'
    previous = json.loads(parent.read_text())
    assert previous['passed'] and previous['platform'] == 'linux/arm64'
    assert previous['native_version'] == 'v176' and previous['image_id'] == args.image_id
    for name, digest in previous['files'].items():
        assert sha(Path(name)) == digest, name
    source = json.loads((workspace / 'source_identity.json').read_text())
    assert source['version'] == 'v191' and source['native_parent'] == 'v176'
    origins = json.loads((HERE / 'native_sources.json').read_text())
    assert origins['parent_files'] == json.loads((task / 'recovery_v176/source_identity.json').read_text())['files']
    assert source['files'] == origins['expected_files']
    actual = {'src/' + str(p.relative_to(workspace / 'src')): sha(p)
              for p in (workspace / 'src').rglob('*') if p.is_file()}
    assert actual == source['files'], 'Native source file set differs from inventory'
    assert source['deleted'] == origins['deleted_files'] and len(source['deleted']) == 33
    assert source['changes'] == origins['changed_files'] and len(source['changes']) == 37
    for name in origins['changed_files']:
        assert sha(HERE / name) == actual[name], name
    for name, digest in source['files'].items():
        assert sha(workspace / name) == digest, name
    prefixes = {ET.parse(path).getroot().findtext('name'): None
                for path in (workspace / 'src').glob('*/package.xml')}
    assert len(prefixes) == 14, prefixes
    prefixes = {name: get_package_prefix(name) for name in prefixes}
    for name in ('lite3_nav2_interfaces', 'scan_planner_msgs', 'lite3_nav2_plugins', 'plan_env',
                 'bspline_opt', 'path_searching', 'traj_utils', 'scan_planner',
                 'scan_nav2_controller', 'lite3_nav2_bridge', 'scan_reactive_tracker'):
        assert prefixes[name] == str(workspace / 'install' / name), (name, prefixes[name])
    assert prefixes['pct_planner'] == str(task / 'recovery_v174/install/pct_planner')
    xml_files = sorted((workspace / 'build/scan_nav2_controller/test_results/scan_nav2_controller').glob('*.gtest.xml'))
    assert len(xml_files) == 3, xml_files
    cases = {}
    for path in xml_files:
        root = ET.parse(path).getroot()
        tests = root.findall('.//testcase')
        assert tests and all(not list(test) and test.get('status') == 'run' for test in tests), path
        assert int(root.get('failures', '0')) == 0 and int(root.get('errors', '0')) == 0, path
        cases[path.name] = [test.get('classname') + '.' + test.get('name') for test in tests]
    assert {name: len(rows) for name, rows in cases.items()} == {
        'test_controller.gtest.xml': 20, 'test_tracking_parity.gtest.xml': 1,
        'test_executor_shutdown.gtest.xml': 1}, cases
    expected_heading = {
        'PluginTest.RouteHeadingDefaultsOffAtExpiredStoppedStub',
        'PluginTest.RouteLookaheadDistanceMustBeFiniteAndPositive',
        'RouteHeadingTest.ExpiredStoppedStubTurnsThroughBothHeadingBands',
        'RouteHeadingTest.SameGoalRefreshChangesHeadingAndPreservesGoalLatch',
        'RouteHeadingTest.ReverseStubKeepsOriginalBodyHeading',
        'RouteHeadingTest.PillarUTurnUsesForwardRouteBeyondExpiredStub',
        'RouteHeadingTest.FinalGoalCaptureOwnsYawBeforeAndAfterLatch'}
    assert {'scan_nav2_controller.' + name for name in expected_heading} <= set(cases['test_controller.gtest.xml'])
    log = task / 'evidence/v191_native_build.log'
    output = log.read_text()
    for marker in ('Summary: 45 tests, 0 errors, 0 failures, 0 skipped',
                   'V176_TERMINAL_CAPTURE_PASS', 'V191_CORNER_LOOKAHEAD_PASS', 'Ran 2 tests', '\nOK\n'):
        assert marker in output, marker
    files = dict(previous['files'])
    for directory in ('src', 'install'):
        for path in (workspace / directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                files[str(path)] = sha(path)
    files[str(workspace / 'source_identity.json')] = sha(workspace / 'source_identity.json')
    tests = dict(unique_gtest_cases=22, controller_gtest_cases=20,
                 route_heading_cases=sorted(expected_heading), gtest_cases=cases,
                 colcon_summary=dict(tests=45, errors=0, failures=0, skipped=0),
                 generated_profile_cases=2, terminal_markers=['V176_TERMINAL_CAPTURE_PASS', 'V191_CORNER_LOOKAHEAD_PASS'],
                 test_xml_sha256={str(path): sha(path) for path in xml_files})
    receipt = dict(passed=True, platform='linux/arm64', ros_distro='foxy', variant='candidate',
                   native_version='v191', image_id=args.image_id, files=files,
                   native_packages_available=len(prefixes), package_prefixes=prefixes,
                   source_identity_sha256=sha(workspace / 'source_identity.json'),
                   underlay_receipt_sha256=sha(parent), underlay_native_version='v176',
                   test_log_sha256=sha(log), tests=tests,
                   claim='Mac Option B component verification only; graph and physical route qualification are separate.')
    path = task / 'evidence/v191_native_receipt.json'
    path.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'passed': True, 'files': len(files), 'native_packages_available': len(prefixes),
                      'unique_gtest_cases': 22, 'receipt_sha256': sha(path)}))


if __name__ == '__main__':
    main()
