"""Require native v196 ARM64 source/install and v196 harness preflight evidence."""
from pathlib import Path
import hashlib
import json
import os
import platform
import subprocess

HERE = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def validate_quality(quality):
    required = dict(passed=True, native_version='v196', execution_platform='linux/arm64',
                    native_packages_available=14, rebuilt_packages=11,
                    global_replan_hz=1.0, reactive_cloud_max_age_s=0.35, cached_path_replay_enabled=True,
                    unique_controller_gtest_cases=29, controller_gtest_cases=27,
                    native_terminal_regressions=True, generated_profile_cases=2,
                    actual_graph_verified=True, full_navigation_accepted=False)
    for key, expected in required.items():
        if key not in quality or type(quality[key]) is not type(expected) or quality[key] != expected:
            raise ValueError('Missing or incorrect quality field: ' + key)
    summary = quality.get('native_colcon_summary', {})
    if (type(summary.get('tests')) is not int or summary['tests'] < 70 or
            any(type(summary.get(k)) is not int or summary[k] != 0 for k in ('errors', 'failures', 'skipped'))):
        raise ValueError('Unqualified native test summary')
    if not isinstance(quality.get('host_tests'), int) or quality['host_tests'] <= 0:
        raise ValueError('Missing successful host test count')
    digests = [quality.get('runtime_receipts', {}).get('candidate'),
               quality.get('native_graph_preflight_sha256'), quality.get('overlay_loaded_sha256'),
               quality.get('host_test_results_sha256')]
    if any(not isinstance(value, str) or len(value) != 64 or
           any(c not in '0123456789abcdef' for c in value) for value in digests):
        raise ValueError('Missing evidence digest')
    return quality


def verify(build, manifest):
    if build.resolve() != HERE or sha(HERE/'quality.json') != manifest['quality_sha256']:
        raise ValueError('Wrong source or component quality identity')
    variant = os.environ['V196_VARIANT']
    if variant != 'candidate':
        raise ValueError('Only the tested Mac candidate is qualified')
    path = Path(os.environ['V196_BUILD_EVIDENCE'])/'build_receipt.json'
    quality = json.loads((HERE/'quality.json').read_text())
    validate_quality(quality)
    receipt = json.loads(path.read_text())
    if not quality['passed'] or sha(path) != quality['runtime_receipts'][variant]:
        raise ValueError('Unqualified source/install receipt')
    if (platform.system(), platform.machine()) != ('Darwin', 'arm64'):
        raise ValueError('This quality receipt qualifies only the Mac ARM64 cohort')
    if (not receipt['passed'] or receipt['platform'] != quality['execution_platform']
            or receipt['variant'] != variant or receipt['native_version'] != 'v196'
            or receipt['native_packages_available'] != 14):
        raise ValueError('Wrong execution platform/variant')
    container = os.environ['V196_NATIVE_CONTAINER']
    image = subprocess.check_output(['docker', 'inspect', '--format', '{{.Image}}', container], text=True).strip()
    if image != receipt['image_id']:
        raise ValueError('Image differs from tested image')
    script = '''from pathlib import Path
import hashlib,json,sys
r=json.loads(Path(sys.argv[1]).read_text())
for name,expected in r['files'].items():
 assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected,name
print('V196_NATIVE_IDENTITY_PASS')
'''
    result = subprocess.run(['docker', 'exec', container, 'python3', '-c', script, str(path)],
                            capture_output=True, text=True, check=True, timeout=90)
    if 'V196_NATIVE_IDENTITY_PASS' not in result.stdout:
        raise ValueError('Missing native identity witness')
    return {'passed': True, 'variant': variant, 'receipt_sha256': sha(path), 'physics_acceptance': False}
