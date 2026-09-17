"""Freeze a clean canonical planner tree plus explicit hash-checked Foxy edits."""

import difflib
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
NAV = Path('/Users/sun/tongbu/study/phdproject/machine-dog-nav')
UPSTREAM = NAV / 'references/upstream/2026-09-04_pct_scan_stairs/PCT-SCAN-ROS2'
COMMIT = '1cf45a1c12ca785ce533293302be09d51daf0ccb'


def sha(content):
    return hashlib.sha256(content).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-C', str(UPSTREAM), *args])


def preserve(path, content):
    if path.exists() and path.read_bytes() != content:
        raise RuntimeError(f'Refusing changed frozen artifact: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def main():
    if Path(git('rev-parse', '--show-toplevel').decode().strip()) != UPSTREAM:
        raise RuntimeError('Expected a separate canonical upstream checkout')
    manifest_path = NAV / 'integration/pct_scan_upstream_ws/UPSTREAM_MANIFEST.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest['commit'] != COMMIT:
        raise RuntimeError('Unexpected upstream identity')
    preserve(ROOT / 'native_planner_manifest.original.json', manifest_path.read_bytes())
    patches = []
    exported = []
    for entry in manifest['files']:
        relative = entry['local_path'].removeprefix('integration/pct_scan_upstream_ws/')
        base = git('show', f"{COMMIT}:{entry['upstream_path']}")
        ported = (NAV / entry['local_path']).read_bytes()
        if sha(base) != entry['upstream_sha256'] or sha(ported) != entry['local_sha256']:
            raise RuntimeError(f'Manifest drift: {relative}')
        preserve(ROOT / 'source/pct_scan_base' / relative, base)
        edits = []
        lines = base.decode().splitlines(keepends=True)
        result = []
        previous = 0
        modified = ported.decode().splitlines(keepends=True)
        for tag, start, end, new_start, new_end in difflib.SequenceMatcher(a=lines, b=modified, autojunk=False).get_opcodes():
            if tag == 'equal':
                continue
            edit = {'start_line_zero_based': start, 'old_lines': lines[start:end], 'new_lines': modified[new_start:new_end]}
            edits.append(edit)
            result.extend(lines[previous:start])
            result.extend(edit['new_lines'])
            previous = end
        result.extend(lines[previous:])
        rebuilt = ''.join(result).encode()
        if rebuilt != ported:
            raise RuntimeError(f'Patch reconstruction failed: {relative}')
        preserve(ROOT / 'source/pct_scan_foxy' / relative, rebuilt)
        exported.append({'path': relative, 'base_sha256': sha(base), 'ported_sha256': sha(rebuilt)})
        if edits:
            patches.append({'path': relative, 'upstream_path': entry['upstream_path'],
                            'base_sha256': sha(base), 'ported_sha256': sha(rebuilt),
                            'declared_adaptations': entry['adaptations'], 'edits': edits})
    # Global PCT source and mixed-license notices are separate from the six ROS packages.
    global_files = git('ls-tree', '-r', '--name-only', COMMIT, 'src/pct', 'LICENSES', 'THIRD_PARTY_NOTICES.md').decode().splitlines()
    global_hashes = {}
    for relative in global_files:
        content = git('show', f'{COMMIT}:{relative}')
        preserve(ROOT / 'source/pct_global' / relative, content)
        global_hashes[relative] = sha(content)
    preserve(ROOT / 'foxy_adaptations.json', (json.dumps(patches, indent=2) + '\n').encode())
    result = {'canonical_url': 'https://github.com/yagami-light7/PCT-SCAN-ROS2',
              'commit': COMMIT, 'import_method': 'committed blobs plus explicit verified line edits',
              'planner_files': exported, 'adapted_files': len(patches),
              'global_pct_and_notices': global_hashes, 'runtime_executed': False,
              'patch_source': str(manifest_path), 'patch_source_sha256': sha(manifest_path.read_bytes())}
    (ROOT / 'native_planner_acquisition.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'planner_files': len(exported), 'explicit_adaptations': len(patches),
                      'global_pct_and_notices': len(global_files), 'all_hashes_match': True}))


if __name__ == '__main__':
    main()
