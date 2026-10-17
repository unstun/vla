"""Verify newly produced regression XML and preserve the accepted v232 receipt."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def verify(work, started_ns, attempt):
    evidence = work / 'evidence' / attempt
    result = evidence / 'test-result.log'
    assert result.stat().st_mtime_ns >= started_ns
    assert 'Summary: 186 tests, 0 errors, 0 failures, 0 skipped' in result.read_text()
    cases = []
    xml_files = list((work / 'build').glob('*/test_results/**/*.xml'))
    assert xml_files, 'No new native test results'
    for path in xml_files:
        assert path.stat().st_mtime_ns >= started_ns, f'Stale test XML: {path}'
        tree = ET.parse(path).getroot()
        for suite in tree.iter('testsuite'):
            assert all(int(suite.attrib.get(key, 0)) == 0
                       for key in ('errors', 'failures', 'skipped', 'disabled')), path
        for case in tree.findall('.//testcase'):
            cases.append((str(path.relative_to(work / 'build')), case.get('classname'), case.get('name')))
    assert len(cases) == len(set(cases)) == 165, len(cases)
    return dict(passed=True, physics_steps=0, unique_test_cases=len(cases), colcon_records=186,
                started_ns=started_ns, xml_files=len(xml_files),
                test_result_sha256=hashlib.sha256(result.read_bytes()).hexdigest(),
                cases=cases)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--started-ns', type=int, required=True)
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    args.output.write_text(json.dumps(verify(args.work, args.started_ns, args.attempt), indent=2) + '\n')
