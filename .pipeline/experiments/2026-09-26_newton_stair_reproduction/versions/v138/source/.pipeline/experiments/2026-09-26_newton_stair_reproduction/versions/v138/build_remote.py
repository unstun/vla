"""Build an isolated v138 export from the verified v137 source on gpu5070ti."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
TASK = Path('/data/sun/vla_mppi_20261009')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert HERE.is_relative_to(TASK/'repo')
    parent = TASK/'recovery_v137'
    output = TASK/'results/recovery_v138'
    output.mkdir(exist_ok=False)
    workspace = TASK/'recovery_v138'
    workspace.mkdir(exist_ok=False)
    previous = json.loads((parent/'source_identity.json').read_text())
    for name, expected in previous['files'].items():
        assert sha(parent/name) == expected, name
        destination = workspace/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(parent/name, destination)
    origins = json.loads((HERE/'native_sources.json').read_text())
    source = dict(previous['files'])
    changed = []
    for path in sorted((HERE/'src').rglob('*')):
        if not path.is_file():
            continue
        name = str(path.relative_to(HERE))
        if name in origins:
            assert sha(parent/name) == origins[name]['parent_sha256'], name
            assert sha(HERE.parent/origins[name]['parent']/name) == origins[name]['parent_sha256'], name
        else:
            assert not (parent/name).exists(), name
        destination = workspace/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        source[name] = sha(destination)
        changed.append(name)
    identity = {'version': 'v138', 'native_parent': 'v137',
                'parent_source_identity_sha256': sha(parent/'source_identity.json'),
                'changes': changed, 'files': source}
    (workspace/'source_identity.json').write_text(json.dumps(identity, indent=2)+'\n')
    receipt_path = TASK/'results/recovery_v137/candidate_receipt.json'
    original = json.loads(receipt_path.read_text())
    # Check all parent source/install bytes before using them as the control.
    for name, expected in original['files'].items():
        assert sha(TASK/Path(name).relative_to('/task')) == expected, name
    baseline = dict(original, variant='baseline', parent_receipt_sha256=sha(receipt_path))
    global_map=json.loads((HERE/'global_map_input.json').read_text())
    baseline['files']=dict(original['files'])
    baseline['files'][global_map['file']]=global_map['map_sha256']
    (output/'baseline_receipt.json').write_text(json.dumps(baseline, indent=2)+'\n')
    script = '''set -eo pipefail
source /opt/ros/foxy/setup.bash
cd /task/recovery_v138
cmake -S third_party/osqp -B dependencies/osqp-build -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DCMAKE_INSTALL_PREFIX="$PWD/dependencies/osqp-install" -DFETCHCONTENT_SOURCE_DIR_QDLDL="$PWD/third_party/qdldl" -DOSQP_BUILD_DEMO_EXE=OFF -DOSQP_BUILD_UNITTESTS=OFF
cmake --build dependencies/osqp-build -j2
cmake --install dependencies/osqp-build
export CMAKE_PREFIX_PATH="$PWD/dependencies/osqp-install:${CMAKE_PREFIX_PATH:-}"
export MAKEFLAGS=-j2
colcon build --base-paths src --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DBUILD_TESTING=ON -DPython3_EXECUTABLE=/usr/bin/python3
colcon test --base-paths src --packages-select scan_nav2_controller lite3_nav2_plugins --executor sequential --return-code-on-test-failure
colcon test-result --verbose
'''
    (output/'build.sh').write_text(script)
    command = ['docker', 'run', '--rm', '--network=none', '--cpus=6', '--memory=12g',
               '-v', f'{TASK}:/task:rw', '--entrypoint', '/bin/bash', original['image_id'],
               '/task/results/recovery_v138/build.sh']
    (output/'build_request.json').write_text(json.dumps({'command': command,
        'source_identity_sha256': sha(workspace/'source_identity.json'),
        'builder_sha256': sha(Path(__file__))}, indent=2)+'\n')
    with (output/'build.log').open('w') as stream:
        subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=900)
    text = (output/'build.log').read_text()
    assert '14 packages finished' in text and '0 failures' in text and '0 errors' in text
    files = {}
    for directory in ('src', 'install', 'dependencies/osqp-install'):
        for path in (workspace/directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                files['/task/'+str(path.relative_to(TASK))] = sha(path)
    for name in ('source_identity.json',):
        files['/task/recovery_v138/'+name] = sha(workspace/name)
    coverage = json.loads((HERE/'support_coverage_input.json').read_text())
    coverage_path = TASK/Path(coverage['file']).relative_to('/task')
    assert sha(coverage_path)==coverage['sha256']
    files[coverage['file']]=coverage['sha256']
    global_map=json.loads((HERE/'global_map_input.json').read_text())
    assert sha(TASK/Path(global_map['file']).relative_to('/task'))==global_map['map_sha256']
    files[global_map['file']]=global_map['map_sha256']
    candidate = dict(passed=True, platform='linux/amd64', ros_distro='foxy',
        variant='candidate', native_version='v138', image_id=original['image_id'], files=files,
        source_identity_sha256=sha(workspace/'source_identity.json'),
        test_log_sha256=sha(output/'build.log'))
    (output/'candidate_receipt.json').write_text(json.dumps(candidate, indent=2)+'\n')
    print(json.dumps({'passed': True, 'native_packages': 14, 'source_files': len(source),
                      'receipt_files': len(files)}), flush=True)

if __name__ == '__main__':
    main()
