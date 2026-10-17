"""Verify exact Mac native sources, installed overlays and re-executed test evidence."""
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
    workspace = task / 'recovery_v189'
    parent = task / 'evidence/v176_native_receipt.json'
    previous = json.loads(parent.read_text())
    assert previous['passed'] and previous['platform'] == 'linux/arm64'
    assert previous['native_version'] == 'v176' and previous['image_id'] == args.image_id
    for name, digest in previous['files'].items():
        assert sha(Path(name)) == digest, name
    source = json.loads((workspace / 'source_identity.json').read_text())
    assert source['version'] == 'v189' and source['native_parent'] == 'v176'
    assert source['files'] == json.loads((HERE / 'native_sources.json').read_text())['expected_files']
    for name, digest in source['files'].items():
        assert sha(workspace / name) == digest, name
    prefixes = {ET.parse(path).getroot().findtext('name'): None
                for path in (workspace / 'src').glob('*/package.xml')}
    assert len(prefixes) == 14, prefixes
    prefixes = {name: get_package_prefix(name) for name in prefixes}
    for name in ('scan_nav2_controller', 'lite3_nav2_bridge'):
        assert prefixes[name] == str(workspace / 'install' / name)
    for name, version in [('pct_planner', 'v174'), ('lite3_nav2_plugins', 'v172'), ('scan_planner', 'v167')]:
        assert prefixes[name] == str(task / ('recovery_' + version) / 'install' / name)
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
        'test_controller.gtest.xml': 44, 'test_tracking_parity.gtest.xml': 1,
        'test_executor_shutdown.gtest.xml': 1}, cases
    expected_heading = {
        'PluginTest.RouteHeadingDefaultsOffAtExpiredStoppedStub',
        'PluginTest.RouteLookaheadDistanceMustBeFiniteAndPositive',
        'RouteHeadingTest.ExpiredStoppedStubTurnsThroughBothHeadingBands',
        'RouteHeadingTest.SameOwnerRefreshChangesHeadingAndPreservesGoalLatch',
        'RouteHeadingTest.ReverseStubKeepsOriginalBodyHeading',
        'RouteHeadingTest.PillarUTurnUsesForwardRouteBeyondExpiredStub',
        'RouteHeadingTest.FinalGoalCaptureOwnsYawBeforeAndAfterLatch'}
    assert {'scan_nav2_controller.' + name for name in expected_heading} <= set(cases['test_controller.gtest.xml'])
    log = task / 'evidence/v189_native_build.log'
    output = log.read_text()
    for marker in ('2 packages finished', 'Summary: 49 tests, 0 errors, 0 failures, 0 skipped',
                   'V176_TERMINAL_CAPTURE_PASS', 'V189_CORNER_LOOKAHEAD_PASS', 'Ran 2 tests', '\nOK\n'):
        assert marker in output, marker
    files = dict(previous['files'])
    for directory in ('src', 'install'):
        for path in (workspace / directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                files[str(path)] = sha(path)
    files[str(workspace / 'source_identity.json')] = sha(workspace / 'source_identity.json')
    tests = dict(unique_gtest_cases=46, controller_gtest_cases=44,
                 route_heading_cases=sorted(expected_heading), gtest_cases=cases,
                 colcon_summary=dict(tests=49, errors=0, failures=0, skipped=0),
                 generated_profile_cases=2, terminal_markers=['V176_TERMINAL_CAPTURE_PASS', 'V189_CORNER_LOOKAHEAD_PASS'],
                 test_xml_sha256={str(path): sha(path) for path in xml_files})
    receipt = dict(passed=True, platform='linux/arm64', ros_distro='foxy', variant='candidate',
                   native_version='v189', image_id=args.image_id, files=files,
                   native_packages_available=len(prefixes), package_prefixes=prefixes,
                   source_identity_sha256=sha(workspace / 'source_identity.json'),
                   underlay_receipt_sha256=sha(parent), underlay_native_version='v176',
                   test_log_sha256=sha(log), tests=tests,
                   claim='Mac component verification only; graph and physical route qualification are separate.')
    path = task / 'evidence/v189_native_receipt.json'
    with path.open('x') as stream:
        stream.write(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'passed': True, 'files': len(files), 'native_packages_available': len(prefixes),
                      'unique_gtest_cases': 46, 'receipt_sha256': sha(path)}))


if __name__ == '__main__':
    main()
