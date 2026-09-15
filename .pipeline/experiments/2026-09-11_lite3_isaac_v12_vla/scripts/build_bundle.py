#!/usr/bin/env python3
"""Assemble the Phase A transport bundle from pinned local inputs.

Verifies every SHA256SUMS.txt BEFORE packing, so a corrupted local tree can never be shipped, and
records the archive's own SHA-256 so the execution host can prove it received the same bytes.

    python3 scripts/build_bundle.py            # writes setup/bundle/phase_a_bundle.tar.gz
    python3 scripts/build_bundle.py --verify-only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tarfile
import time

REPO = pathlib.Path(__file__).resolve().parents[4]
EXP = pathlib.Path(__file__).resolve().parents[1]
BRIDGE = REPO / 'references/upstream/2026-09-11_lite3_sim_bridge'
V12 = REPO / 'references/upstream/2026-09-11_lite3_v12_locomotion'
OUT_DIR = EXP / 'setup/bundle'
ARCHIVE = OUT_DIR / 'phase_a_bundle.tar.gz'

# macOS tar/AppleDouble junk must never reach a Linux host; it also perturbs directory hashes.
EXCLUDE_NAMES = {'.DS_Store'}
EXCLUDE_PREFIXES = ('._',)
EXCLUDE_DIRS = {'__pycache__'}


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksums(root: pathlib.Path) -> int:
    """Re-verify a vendored tree against its own SHA256SUMS.txt. Returns the file count."""
    sums = root / 'SHA256SUMS.txt'
    entries = [line for line in sums.read_text().splitlines() if line.strip()]
    bad = []
    for line in entries:
        expected, rel = line.split(None, 1)
        rel = rel.strip()
        target = root / rel
        if not target.is_file():
            bad.append(f'MISSING {rel}')
        elif sha256_file(target) != expected:
            bad.append(f'MISMATCH {rel}')
    if bad:
        raise SystemExit(f'{root.name}: refusing to build a bundle from a divergent tree:\n  ' + '\n  '.join(bad))
    print(f'  {root.name}: {len(entries)} files, all match SHA256SUMS.txt')
    return len(entries)


def should_skip(path: pathlib.Path) -> bool:
    name = path.name
    return (
        name in EXCLUDE_NAMES
        or name.startswith(EXCLUDE_PREFIXES)
        or name in EXCLUDE_DIRS
        or path.suffix == '.pyc'
    )


def add_tree(tar: tarfile.TarFile, root: pathlib.Path, arc_root: str) -> int:
    count = 0
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        # Skip the file and anything living under an excluded directory such as __pycache__.
        if any(should_skip(pathlib.Path(part)) for part in rel.parts):
            continue
        info = tar.gettarinfo(str(path), arcname=f'{arc_root}/{rel.as_posix()}')
        # Deterministic metadata: the archive hash should depend on content, not on the build clock.
        info.uid = info.gid = 0
        info.uname = info.gname = 'root'
        info.mtime = 0
        with open(path, 'rb') as handle:
            tar.addfile(info, handle)
        count += 1
    return count


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-only', action='store_true', help='check the pinned trees and stop')
    args = parser.parse_args(argv)

    print('Verifying pinned inputs before packing:')
    n_bridge = verify_checksums(BRIDGE)
    n_v12 = verify_checksums(V12)
    if args.verify_only:
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if ARCHIVE.exists():
        raise SystemExit(f'{ARCHIVE} already exists; delete it deliberately rather than overwriting evidence')

    os.environ['COPYFILE_DISABLE'] = '1'
    started = time.time()
    packed = {}
    with tarfile.open(ARCHIVE, 'w:gz') as tar:
        packed['lite3_sim_bridge'] = add_tree(tar, BRIDGE / 'source', 'lite3_sim_bridge')
        packed['v12_runtime'] = add_tree(tar, V12 / 'source/v12_runtime', 'v12_runtime')
        packed['checkpoint'] = add_tree(tar, V12 / 'source/checkpoint', 'checkpoint')
        for extra in (BRIDGE / 'SHA256SUMS.txt', BRIDGE / 'SOURCE.md', V12 / 'SHA256SUMS.txt', V12 / 'SOURCE.md'):
            arc = f'provenance/{extra.parent.name}__{extra.name}'
            info = tar.gettarinfo(str(extra), arcname=arc)
            info.uid = info.gid = 0
            info.uname = info.gname = 'root'
            info.mtime = 0
            with open(extra, 'rb') as handle:
                tar.addfile(info, handle)

    record = {
        'archive': str(ARCHIVE.relative_to(REPO)),
        'archive_sha256': sha256_file(ARCHIVE),
        'archive_bytes': ARCHIVE.stat().st_size,
        'build_seconds': round(time.time() - started, 1),
        'packed_files': packed,
        'verified_before_packing': {'lite3_sim_bridge': n_bridge, 'v12_locomotion': n_v12},
        'excluded': sorted(EXCLUDE_DIRS | EXCLUDE_NAMES | {'._*', '*.pyc'}),
        'layout': {
            'lite3_sim_bridge/': 'importable package root; put it first on PYTHONPATH',
            'v12_runtime/': 'source/robot_lab and source/rsl_rl live here',
            'checkpoint/model_149999.pt': 'fail-closed SHA-256 gate inside the adapter',
            'provenance/': 'the two SOURCE.md and SHA256SUMS.txt files, so the host carries its own proof',
        },
    }
    (OUT_DIR / 'bundle_manifest.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
