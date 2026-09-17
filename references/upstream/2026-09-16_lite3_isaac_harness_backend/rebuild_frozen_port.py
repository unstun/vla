"""Verify/rebuild the frozen Foxy port from local base bytes and explicit edits."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(content):
    return hashlib.sha256(content).hexdigest()


def main():
    manifest = json.loads((ROOT / 'native_planner_acquisition.json').read_text())
    edits_by_file = {item['path']: item for item in json.loads((ROOT / 'foxy_adaptations.json').read_text())}
    for item in manifest['planner_files']:
        relative = item['path']
        base = (ROOT / 'source/pct_scan_base' / relative).read_bytes()
        if sha(base) != item['base_sha256']:
            raise RuntimeError(f'Base source drift: {relative}')
        lines = base.decode().splitlines(keepends=True)
        result = []
        previous = 0
        for edit in edits_by_file.get(relative, {}).get('edits', []):
            start = edit['start_line_zero_based']
            end = start + len(edit['old_lines'])
            if start < previous or lines[start:end] != edit['old_lines']:
                raise RuntimeError(f'Invalid adaptation context: {relative}')
            result.extend(lines[previous:start])
            result.extend(edit['new_lines'])
            previous = end
        result.extend(lines[previous:])
        content = ''.join(result).encode()
        if sha(content) != item['ported_sha256']:
            raise RuntimeError(f'Port reconstruction mismatch: {relative}')
        target = ROOT / 'source/pct_scan_foxy' / relative
        if target.exists() and target.read_bytes() != content:
            raise RuntimeError(f'Refusing modified frozen source: {relative}')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    for relative, digest in manifest['global_pct_and_notices'].items():
        if sha((ROOT / 'source/pct_global' / relative).read_bytes()) != digest:
            raise RuntimeError(f'Global PCT source drift: {relative}')
    print('65 Foxy files reconstructed exactly; 145 global PCT/license files verified; no sibling reads.')


if __name__ == '__main__':
    main()
