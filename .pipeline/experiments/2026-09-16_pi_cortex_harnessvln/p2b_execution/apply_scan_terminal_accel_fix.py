#!/usr/bin/env python3
"""Apply the one-line SCAN terminal-acceleration fix to a freshly materialized build.

The step is hash-gated and recorded. It refuses unless planner_manager.cpp is
the recorded pinned base file and line 171 is the exact defect line. It changes
`evaluateAcc(t)` to `evaluateAcc(time)` on that line only, preserves every line
terminator (the file mixes CRLF and LF), and writes
`terminal_accel_fix_manifest.json` beside `src/`. It must run before
`build_scan.py` records the source manifest.
"""
import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET_REL = 'src/plan_manage/src/planner_manager.cpp'
# Pinned PCT-SCAN-ROS2 base and scan_03 copy of planner_manager.cpp.
BASE_SHA256 = '0c51df6396f32d2563d50be0a16f3346c82a5c4d5659acb18b898da1df463981'
LINE_NUMBER = 171
BEFORE_LINE = '        start_end_derivatives.push_back(gl_traj.evaluateAcc(t));'
AFTER_LINE = '        start_end_derivatives.push_back(gl_traj.evaluateAcc(time));'
MANIFEST_NAME = 'terminal_accel_fix_manifest.json'
RATIONALE = {
    'defect': ('Polynomial initialization supplies the acceleration at the last sample strictly before the '
               'polynomial end as the terminal acceleration.'),
    'time_is_true_end': [
        'planner_manager.cpp:124 declares `double time`, the requested polynomial duration, in the enclosing block.',
        'planner_manager.cpp:128 builds one segment of duration `time` with end acceleration Eigen::Vector3d::Zero().',
        'planner_manager.cpp:141-143 builds two segments of `time / 2` each (total `time`) with end acceleration Zero().',
        'planner_manager.cpp:155 samples `for (t = 0; t < time; t += ts)` and line 167 applies `t -= ts`, so `t` is the '
        'last sample, strictly before `time`.',
        'planner_manager.cpp:169 already supplies the requested end velocity, local_target_vel, not a sampled value.',
        'planner_manager.cpp:242 (previous-trajectory branch) already supplies a zero end acceleration.',
        'traj_utils/include/traj_utils/polynomial_traj.h:131-139 evaluateAcc(t) locates the segment with a 1e-4 s '
        'tolerance, so evaluateAcc(time) evaluates the last segment at its end.',
    ],
    'evidence': [
        '.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_replan_diagnosis/RESULT.md',
        '.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_replan_diagnosis/runs/native_true_end_20260916T180700Z/',
    ],
    'upstream_divergence': ('The base file hash equals the pinned PCT-SCAN-ROS2 base (1cf45a1c). This build diverges from '
                            'that base by this line only; an unmodified official build was not verified.'),
    'unchanged': 'No limit, gate, deadline, optimizer setting or sampling step is changed.',
}


class FixRefused(RuntimeError):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def split_lines(data):
    """Split bytes on LF only, keeping terminators, so numbering matches editors and awk."""
    parts = data.split(b'\n')
    lines = [part + b'\n' for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def line_text(raw):
    """Return a decoded line without its terminator, and the terminator bytes."""
    for ending in (b'\r\n', b'\n'):
        if raw.endswith(ending):
            return raw[:-len(ending)].decode('utf-8'), ending
    return raw.decode('utf-8'), b''


def apply_fix(build_dir, expected_sha256=BASE_SHA256, now=None):
    build_dir = Path(build_dir).resolve()
    target = build_dir / TARGET_REL
    manifest_path = build_dir / MANIFEST_NAME
    if manifest_path.exists():
        raise FixRefused('fix manifest already exists: ' + str(manifest_path))
    for name in ('build_result.json', 'source_sha256.json'):
        if (build_dir / name).exists():
            raise FixRefused('build already recorded %s; the fix must precede build_scan.py' % name)
    if not target.is_file():
        raise FixRefused('target file missing: ' + str(target))
    before = target.read_bytes()
    lines = split_lines(before)
    if len(lines) < LINE_NUMBER:
        raise FixRefused('target file has fewer than %d lines' % LINE_NUMBER)
    current, ending = line_text(lines[LINE_NUMBER - 1])
    if current == AFTER_LINE:
        raise FixRefused('fix already applied at line %d' % LINE_NUMBER)
    before_sha = sha256_bytes(before)
    if before_sha != expected_sha256:
        raise FixRefused('base hash mismatch: %s != %s' % (before_sha, expected_sha256))
    if current != BEFORE_LINE:
        raise FixRefused('line %d text mismatch: %r' % (LINE_NUMBER, current))
    replaced = current.replace('evaluateAcc(t)', 'evaluateAcc(time)')
    if replaced != AFTER_LINE or current.count('evaluateAcc(t)') != 1:
        raise FixRefused('replacement is not the single recorded token change')
    new_lines = list(lines)
    new_lines[LINE_NUMBER - 1] = replaced.encode('utf-8') + ending
    after = b''.join(new_lines)
    changed = [i + 1 for i, (a, b) in enumerate(zip(lines, new_lines)) if a != b]
    if len(new_lines) != len(lines) or changed != [LINE_NUMBER]:
        raise FixRefused('internal check failed: changed lines %r' % changed)
    diff = ''.join(difflib.unified_diff(
        [line.decode('utf-8') for line in lines],
        [line.decode('utf-8') for line in new_lines],
        fromfile='a/' + TARGET_REL, tofile='b/' + TARGET_REL))
    temporary = target.with_name(target.name + '.fix_tmp')
    temporary.write_bytes(after)
    os.chmod(temporary, target.stat().st_mode & 0o7777)
    temporary.replace(target)
    if target.read_bytes() != after:
        raise FixRefused('written file differs from the computed result')
    script = Path(__file__).resolve()
    manifest = {
        'schema_version': 1,
        'purpose': 'SCAN terminal-acceleration fix (evaluateAcc(t) -> evaluateAcc(time)) for a new materialized build',
        'script': str(script),
        'script_sha256': sha256_bytes(script.read_bytes()),
        'build_dir': str(build_dir),
        'file': TARGET_REL,
        'line_number': LINE_NUMBER,
        'line_terminator': ending.decode('ascii'),
        'before_line': BEFORE_LINE,
        'after_line': AFTER_LINE,
        'before_sha256': before_sha,
        'expected_base_sha256': expected_sha256,
        'after_sha256': sha256_bytes(after),
        'changed_line_numbers': changed,
        'unified_diff': diff,
        'applied_utc': (now or datetime.now(timezone.utc)).isoformat(),
        'rationale': RATIONALE,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build_name', help='Directory name under p2b_execution/builds, e.g. scan_04')
    args = parser.parse_args(argv)
    if not args.build_name.replace('_', '').isalnum():
        raise ValueError('Invalid build name')
    if args.build_name in {'scan_01', 'scan_02', 'scan_03'}:
        raise FixRefused('recorded builds are immutable: ' + args.build_name)
    manifest = apply_fix(HERE / 'builds' / args.build_name)
    print(json.dumps({k: manifest[k] for k in ('file', 'line_number', 'before_sha256', 'after_sha256')}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
