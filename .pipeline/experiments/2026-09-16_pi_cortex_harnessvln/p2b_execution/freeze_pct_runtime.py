"""Capture the exact previously qualified PCT native ABI and pinned Python source."""

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
HOST = 'gpu5070ti'
REMOTE = '/home/sun/machine-dog-nav-runs/2026-09-08_pct_scan_retest'


def main():
    inspected = json.loads((HERE / 'pct_runtime_inspection.json').read_text())
    modules = inspected['inspection']['modules']
    expected = json.loads((HERE / 'baseline_config/pct_inputs.json').read_text())['expected_module_sha256']
    for name, sha in expected.items():
        if modules[name]['sha256'] != sha:
            raise RuntimeError('PCT ABI drift: ' + name)
    paths = set()
    for value in modules.values():
        if value['path'].endswith('.so'):
            paths.add(value['path'])
        paths.update(re.findall(r'(/io/[^\s]+)', value.get('ldd', '')))
    relative = sorted(p.removeprefix('/io/') for p in paths)
    if any('..' in Path(p).parts or p.startswith('/') for p in relative):
        raise ValueError('Non-relative ABI path')
    code = ('import pathlib,hashlib,json\n'
            f'root=pathlib.Path({REMOTE!r})\nfiles={relative!r}\n'
            'print(json.dumps({p:{"sha256":hashlib.sha256((root/p).read_bytes()).hexdigest(),"bytes":(root/p).stat().st_size} for p in files},indent=2))\n')
    response = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', HOST,
                               'python3 -'], input=code, capture_output=True, text=True, check=True, timeout=60)
    hashes = json.loads(response.stdout)
    file_list = HERE / 'pct_binary_files.txt'
    file_list.write_text('\n'.join(relative) + '\n')
    download = HERE / 'pct_runtime' / 'download'
    download.mkdir(parents=True, exist_ok=True)
    subprocess.run(['rsync', '-aL', '--files-from=' + str(file_list),
                    HOST + ':' + REMOTE + '/', str(download) + '/'], check=True, timeout=120)
    runtime = HERE / 'pct_runtime'
    lib = runtime / 'lib'; lib.mkdir(exist_ok=True)
    records = []
    for name in relative:
        source = download / name
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != hashes[name]['sha256']:
            raise RuntimeError('ABI return hash mismatch: ' + name)
        target = lib / source.name
        if target.exists() and target.read_bytes() != data:
            raise RuntimeError('ABI filename collision/drift: ' + target.name)
        target.write_bytes(data)
        records.append({'path': str(target.relative_to(HERE)), 'source': REMOTE + '/' + name,
                        **hashes[name]})
    canonical = ROOT / 'references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_global/src/pct/pct_planner'
    package = runtime / 'python/pct_planner'
    for source in (canonical / 'pct_planner').rglob('*.py'):
        target = package / source.relative_to(canonical / 'pct_planner')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (package / 'lib').mkdir(exist_ok=True)
    shutil.copyfile(canonical / 'lib/__init__.py', package / 'lib/__init__.py')
    for source in lib.glob('*.cpython-310-*.so'):
        shutil.copyfile(source, package / 'lib' / source.name)
    wrapper = package / 'planner_wrapper.py'
    if hashlib.sha256(wrapper.read_bytes()).hexdigest() != expected['pct_planner.planner_wrapper']:
        raise RuntimeError('Pinned wrapper differs from executed wrapper')
    all_files = {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for prefix in [lib, runtime / 'python'] for p in prefix.rglob('*') if p.is_file()}
    record = {'image_id': inspected['image_id'], 'python_abi': 'CPython 3.10 x86_64 Linux',
              'binary_artifacts': records, 'files': all_files,
              'source': 'Pinned canonical PCT Python source and exact earlier qualified native binaries; no new build claim.',
              'regeneration': 'Run inspect_pct_runtime.py then freeze_pct_runtime.py. Native build instructions remain in the pinned canonical PCT source; arbitrary rebuilds need new qualification.',
              'run_environment': {'PYTHONPATH': '/pct-runtime/python', 'LD_LIBRARY_PATH': '/pct-runtime/lib'}}
    (HERE / 'pct_runtime_manifest.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'binary_files': len(records), 'runtime_files': len(all_files), 'hashes_verified': True}, indent=2))


if __name__ == '__main__':
    main()
