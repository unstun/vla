"""Recover exactly the frozen53 requests, then recapture nominal LiDAR at zero physics."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import time

ROOT = Path('/home/ubuntu/sun/vla_v286_20261020')
EXP = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
VERSION = EXP / 'versions/v286'
OUT = ROOT / 'cohort'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert json.loads((ROOT / 'evidence/geometry01_closed.json').read_text())['passed']
    assert not OUT.exists()
    manifest = json.loads((VERSION / 'cases_manifest.json').read_text())
    assert manifest['positive_count'] == manifest['distinct_spatial_pairs'] == 50
    assert manifest['illegal_controls'] == 3 and len(manifest['cases']) == 53
    template = json.loads((EXP / 'inputs/historical_full_building.json').read_text())
    prepared = []
    for case in manifest['cases']:
        scenario = dict(template)
        scenario.update(case_id=case['case_id'], route_profile='generalization',
            spawn_ground_xyz_m=case['start']['ground'], spawn_yaw_rad=case['start']['yaw'],
            goal_ground_xyz_m=case['goal']['ground'], goal_yaw_rad=case['goal']['yaw'],
            profile_source='v262 original-mesh certified pre-score construction',
            scene_condition='Complete original Building; no actor')
        for name in ['native_support_screen', 'initial_center_distance_m', 'initial_placement_pass']:
            scenario.pop(name, None)
        text = json.dumps(scenario, indent=2) + '\n'
        assert hashlib.sha256(text.encode()).hexdigest() == case['scenario_sha256'], case['case_id']
        values = case['start']['ground'][:2] + [case['start']['ground'][2] + .3]
        values += case['goal']['ground'][:2] + [case['goal']['ground'][2] + .3,
            case['start']['yaw'], case['goal']['yaw']]
        endpoints = ' '.join(map(str, values)) + '\n'
        assert hashlib.sha256(endpoints.encode()).hexdigest() == case['endpoints_sha256'], case['case_id']
        prepared.append((case['case_id'], text, endpoints))
    OUT.mkdir()
    for name in ['cases_manifest.json', 'start_admission.json']:
        shutil.copy2(VERSION / name, OUT / name)
    for case, text, endpoints in prepared:
        folder = OUT / 'cases' / case
        folder.mkdir(parents=True)
        (folder / 'scenario.json').write_text(text)
        (folder / 'endpoints.txt').write_text(endpoints)
    receipt = ROOT / 'evidence/cohort01.json'
    report = dict(stage='fixed_requests_verified', physics_steps=0, cases=53,
        original_request_manifest_sha256=sha(VERSION / 'cases_manifest.json'),
        original_native_manifest_sha256=sha(VERSION / 'native_manifest.json'),
        all_scenario_and_endpoint_hashes_match=True, start_certificates_unchanged=True,
        original_captures_unavailable_on_powered_off_9700x=True,
        capture_scope='Fresh zero-step nominal captures onultra9; never claim original capture-byte identity',
        capture_source_sha256=sha(VERSION / 'capture_cases.py'), created_utc_s=time.time())
    receipt.write_text(json.dumps(report, indent=2) + '\n')
    spec = importlib.util.spec_from_file_location('v286_frozen_capture', VERSION / 'capture_cases.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT = OUT  # Host output root only; the frozen sensor/pose code is unchanged.
    module.main()
    report.update(stage='passed', finished_utc_s=time.time(), fixtures={})
    for case in manifest['cases']:
        folder = OUT / 'cases' / case['case_id']
        fixture = json.loads((folder / 'fixture.json').read_text())
        assert fixture['physics_steps'] == 0 and fixture['max_scan_s'] <= .1
        assert fixture['scenario_sha256'] == case['scenario_sha256']
        for relative, expected in fixture['files'].items():
            assert sha(folder / relative) == expected
        report['fixtures'][case['case_id']] = sha(folder / 'fixture.json')
    receipt.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(passed=True, fixed_requests=53, recaptured=53, physics_steps=0)))


if __name__ == '__main__':
    main()
