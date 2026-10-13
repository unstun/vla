"""Verify the original physics packages, policy, scene and frozen runtime inputs."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-root', type=Path, required=True)
    args = parser.parse_args()
    task = args.task_root.resolve()
    assert platform.system() == 'Darwin' and platform.machine() == 'arm64'
    os.environ['WARP_CACHE_PATH'] = str(task / 'cache/preflight-warp')
    sys.path[:0] = [str(task / 'host_python'), str(BASE / 'versions/v40/physics'),
                   str(BASE / 'scripts'), str(BASE / 'runtime_sources/bridge')]
    import newton
    import warp
    import zmq
    from scene_assets import verify_inputs
    from lite3_newton_v40 import verify_inputs as verify_policy
    verify_inputs()
    verify_policy()
    manifest = json.loads((HERE / 'runtime_sync_manifest.json').read_text())
    for name, record in manifest['files'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == record['sha256'], name
    expected = json.loads((HERE.parent / 'v123/results/host_preflight.json').read_text())['packages']
    actual = {name: importlib.metadata.version(name) for name in expected}
    assert actual == expected, (actual, expected)
    result = {'passed': True, 'platform': platform.platform(), 'python': sys.version,
              'physics_advanced': False, 'packages': actual, 'runtime_inputs_verified': len(manifest['files']),
              'claim': 'Same package versions and input bytes; cross-architecture timing and numerical behavior require actual runs.'}
    (task / 'evidence/host_preflight.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
