"""Build the one changed profile package over verified Linuxv175 binaries."""
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
    from resource_gate import admit
    admission = admit()
    parent = TASK/'recovery_v186'
    output = TASK/'results/recovery_v187'; output.mkdir(exist_ok=False)
    workspace = TASK/'recovery_v187'; workspace.mkdir(exist_ok=False)
    previous = json.loads((parent/'source_identity.json').read_text())
    origins = json.loads((HERE/'native_sources.json').read_text())
    assert previous['files'] == origins['parent_files']
    source = dict(previous['files'])
    for name, expected in source.items():
        assert sha(parent/name) == expected, name
        destination = workspace/name; destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(parent/name, destination)
    for name in origins['changed_files']:
        shutil.copyfile(HERE/name, workspace/name); source[name] = sha(workspace/name)
    assert source == origins['expected_files'], 'Must match frozen local native source map'
    identity = {'version':'v187', 'native_parent':'v177', 'linux_binary_underlay':'v186',
                'parent_source_identity_sha256':sha(parent/'source_identity.json'),
                'changes':origins['changed_files'], 'files':source}
    (workspace/'source_identity.json').write_text(json.dumps(identity,indent=2)+'\n')
    receipt_path = TASK/'results/recovery_v186/candidate_receipt.json'
    original = json.loads(receipt_path.read_text())
    for name, expected in original['files'].items():
        assert sha(TASK/Path(name).relative_to('/task')) == expected, name
    (output/'baseline_receipt.json').write_text(json.dumps(dict(original,variant='baseline'),indent=2)+'\n')
    script = '''set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/recovery_v186/install/setup.bash
export MAKEFLAGS=-j2
cd /task/recovery_v187
colcon build --base-paths src --packages-select scan_nav2_controller lite3_nav2_bridge --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
colcon test --packages-select scan_nav2_controller --executor sequential --event-handlers console_direct+
colcon test-result --verbose
source install/setup.bash
python3 /task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v187/test_profile_frames.py
cmake -S /task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v187 -B terminal_build
cmake --build terminal_build -j2
terminal_build/terminal_capture_probe /task/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v187/terminal_fixture.txt
python3 - <<'VERIFY'
from ament_index_python.packages import get_package_prefix
assert get_package_prefix('lite3_nav2_bridge')=='/task/recovery_v187/install/lite3_nav2_bridge'
assert get_package_prefix('scan_nav2_controller')=='/task/recovery_v187/install/scan_nav2_controller'
for package in ['scan_planner','pct_planner','lite3_nav2_plugins']:
 assert get_package_prefix(package)=='/task/recovery_v175/install/'+package
print('V187_UNDERLAY_IDENTITY_PASS')
VERIFY
'''
    (output/'build.sh').write_text(script)
    command = ['docker','run','--rm','--network=none','--cpus=4','--memory=4g',
               '-e','OPENBLAS_NUM_THREADS=1','-e','OMP_NUM_THREADS=1',
               '-v',f'{TASK}:/task:rw','--entrypoint','/bin/bash',original['image_id'],
               '/task/results/recovery_v187/build.sh']
    (output/'build_request.json').write_text(json.dumps({'command':command,'resource_admission':admission,
        'source_identity_sha256':sha(workspace/'source_identity.json'),'builder_sha256':sha(Path(__file__))},indent=2)+'\n')
    with (output/'build.log').open('w') as stream:
        subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=600)
    log = (output/'build.log').read_text()
    assert '2 packages finished' in log and 'V187_TERMINAL_CAPTURE_PASS' in log and 'V187_UNDERLAY_IDENTITY_PASS' in log
    files = dict(original['files'])
    for directory in ('src','install'):
        for path in (workspace/directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                files['/task/'+str(path.relative_to(TASK))] = sha(path)
    files['/task/recovery_v187/source_identity.json'] = sha(workspace/'source_identity.json')
    candidate = dict(passed=True,platform='linux/amd64',ros_distro='foxy',variant='candidate',
        native_version='v187',image_id=original['image_id'],files=files,
        source_identity_sha256=sha(workspace/'source_identity.json'),
        underlay_receipt_sha256=sha(receipt_path),underlay_native_version='v186',
        test_log_sha256=sha(output/'build.log'))
    (output/'candidate_receipt.json').write_text(json.dumps(candidate,indent=2)+'\n')
    print(json.dumps({'passed':True,'available_native_packages':14,'rebuilt_packages':2,
                      'source_files':len(source),'receipt_files':len(files)}),flush=True)


if __name__ == '__main__': main()
