#!/usr/bin/env python3
"""Compare two materialized SCAN source trees and list every difference.

Nothing is ignored: all regular files are compared, and symlinks or empty
directories are listed separately. With --expect-one-line the exit code is
nonzero unless the trees differ in exactly one file and exactly one line.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_scan_terminal_accel_fix import split_lines  # noqa: E402


def tree_entries(root):
    files, other = {}, []
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            other.append({'path': rel, 'kind': 'symlink', 'target': str(path.readlink())})
        elif path.is_file():
            files[rel] = path
        elif path.is_dir() and not any(path.iterdir()):
            other.append({'path': rel, 'kind': 'empty_directory'})
    return files, other


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def line_changes(reference, candidate):
    a, b = split_lines(reference.read_bytes()), split_lines(candidate.read_bytes())
    opcodes = [op for op in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if op[0] != 'equal']
    record = {
        'reference_line_count': len(a),
        'candidate_line_count': len(b),
        'opcodes': [{'tag': tag, 'reference_lines': [i1 + 1, i2], 'candidate_lines': [j1 + 1, j2]}
                    for tag, i1, i2, j1, j2 in opcodes],
        'single_line_replacement': (len(opcodes) == 1 and opcodes[0][0] == 'replace'
                                    and opcodes[0][2] - opcodes[0][1] == 1 and opcodes[0][4] - opcodes[0][3] == 1),
    }
    try:
        record['unified_diff'] = ''.join(difflib.unified_diff(
            [line.decode('utf-8') for line in a], [line.decode('utf-8') for line in b],
            fromfile='reference/' + reference.name, tofile='candidate/' + candidate.name))
    except UnicodeDecodeError:
        record['unified_diff'] = None
    return record


def compare_trees(reference_root, candidate_root):
    reference_root, candidate_root = Path(reference_root).resolve(), Path(candidate_root).resolve()
    ref_files, ref_other = tree_entries(reference_root)
    cand_files, cand_other = tree_entries(candidate_root)
    changed = []
    for rel in sorted(set(ref_files) & set(cand_files)):
        ref_sha, cand_sha = digest(ref_files[rel]), digest(cand_files[rel])
        if ref_sha != cand_sha:
            item = {'path': rel, 'reference_sha256': ref_sha, 'candidate_sha256': cand_sha}
            item.update(line_changes(ref_files[rel], cand_files[rel]))
            changed.append(item)
    only_ref = sorted(set(ref_files) - set(cand_files))
    only_cand = sorted(set(cand_files) - set(ref_files))
    return {
        'schema_version': 1,
        'reference': str(reference_root),
        'candidate': str(candidate_root),
        'reference_file_count': len(ref_files),
        'candidate_file_count': len(cand_files),
        'only_in_reference': only_ref,
        'only_in_candidate': only_cand,
        'reference_other_entries': ref_other,
        'candidate_other_entries': cand_other,
        'changed_files': changed,
        'exactly_one_file_one_line': (not only_ref and not only_cand and not ref_other and not cand_other
                                      and len(changed) == 1 and changed[0]['single_line_replacement']),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference_src', type=Path)
    parser.add_argument('candidate_src', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--expect-one-line', action='store_true')
    args = parser.parse_args(argv)
    result = compare_trees(args.reference_src, args.candidate_src)
    text = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.output:
        if args.output.exists():
            raise FileExistsError('refusing to overwrite ' + str(args.output))
        args.output.write_text(text, encoding='utf-8')
    print(text, end='')
    if args.expect_one_line and not result['exactly_one_file_one_line']:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
