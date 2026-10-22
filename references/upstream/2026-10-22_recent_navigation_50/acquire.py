#!/usr/bin/env python3
"""Acquire pinned, source-only reference checkouts; never run upstream code."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parent
CODE_SUFFIXES = {'.py', '.cpp', '.cc', '.c', '.h', '.hpp', '.rs', '.sh', '.js', '.ts', '.cu', '.cuh', '.jl', '.m', '.ipynb', '.xml', '.launch'}
OMIT_SUFFIXES = ['mp4', 'mov', 'avi', 'webm', 'mkv', 'gif', 'png', 'jpg', 'jpeg', 'tif', 'tiff', 'pdf', 'zip', 'tar', 'gz', '7z', 'rar', 'pt', 'pth', 'ckpt', 'onnx', 'safetensors', 'bag', 'mcap', 'db3', 'npy', 'npz', 'h5', 'hdf5', 'ply', 'pcd', 'stl', 'obj', 'fbx', 'glb', 'gltf', 'usd', 'usdc', 'usdz', 'blend', 'so', 'dll', 'dylib', 'a', 'bin', 'pkl', 'pickle']
PATTERNS = ['/*'] + ['!*.' + suffix for suffix in OMIT_SUFFIXES]
ENV = {**os.environ, 'GIT_LFS_SKIP_SMUDGE': '1', 'GIT_TERMINAL_PROMPT': '0'}


def git(args: list[str], cwd: Path | None = None, timeout: int = 360) -> bytes:
    result = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *args], cwd=cwd, env=ENV,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[-3000:])
    return result.stdout


def inspect(repo: dict, dst: Path) -> dict:
    sha, commit_date, subject = git(['log', '-1', '--format=%H%n%cI%n%s'], dst).decode().splitlines()[:3]
    tree = {}
    # Avoid --long: obtaining omitted blob sizes triggers lazy downloads.
    for raw in git(['ls-tree', '-r', '-z', 'HEAD'], dst).split(b'\0'):
        if not raw:
            continue
        header, name = raw.split(b'\t', 1)
        mode, kind, oid = header.decode().split()
        tree[name.decode()] = {'mode': mode, 'kind': kind, 'git_oid': oid}
    rows, missing, mismatches, lfs, converted = [], [], [], [], []
    for rel, obj in tree.items():
        if obj['kind'] != 'blob':
            continue
        path = dst / rel
        if not path.exists() and not path.is_symlink():
            missing.append(rel)
            continue
        data = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
        oid = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        canonical_oid = oid
        if oid != obj['git_oid']:
            # Git attributes may intentionally materialize CRLF on checkout.
            canonical_oid = git(['hash-object', '--path=' + rel, rel], dst).decode().strip()
            if canonical_oid != obj['git_oid']:
                mismatches.append(rel)
            else:
                converted.append(rel)
        is_lfs = data.startswith(b'version https://git-lfs.github.com/spec/v1\n')
        if is_lfs:
            lfs.append(rel)
        rows.append({'path': rel, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                     'git_oid': obj['git_oid'], 'worktree_git_oid': oid,
                     'symlink': path.is_symlink(), 'lfs_pointer': is_lfs})
    rows.sort(key=lambda x: x['path'])
    code = [x['path'] for x in rows if Path(x['path']).suffix.lower() in CODE_SUFFIXES and not x['lfs_pointer'] and not x['symlink']]
    license_files = [x for x in rows if '/' not in x['path'] and re.match(r'^(licen[cs]e|copying)([._-]|$)', x['path'], re.I)]
    readmes = [x['path'] for x in rows if '/' not in x['path'] and re.match(r'^readme([._-]|$)', x['path'], re.I)]
    if not license_files:
        raise RuntimeError('No root license file found: requires separate review')
    if not code:
        raise RuntimeError('No implementation source found')
    if mismatches:
        raise RuntimeError('Git blob mismatch: ' + repr(mismatches[:5]))
    dirty = git(['status', '--porcelain', '--untracked-files=no'], dst).decode().strip()
    if dirty:
        raise RuntimeError('Checkout is dirty: ' + dirty[:1000])
    manifest = json.dumps(rows, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    slug = repo['name'].replace('/', '__')
    (ROOT/'raw_logs'/f'{slug}.files.json').write_text(manifest)
    (ROOT/'raw_logs'/f'{slug}.omitted.json').write_text(json.dumps(missing, indent=2) + '\n')
    text = '\n'.join((dst/p).read_text(errors='replace') for p in readmes[:2])
    (ROOT/'raw_logs'/f'{slug}.readme.txt').write_text(text)
    license_preview = {x['path']: (dst/x['path']).read_text(errors='replace')[:1600] for x in license_files}
    if repo.get('pinned_commit') and sha != repo['pinned_commit']:
        raise RuntimeError('Pinned commit mismatch')
    return {**repo, 'status': 'imported', 'pinned_commit': sha, 'commit_date': commit_date, 'commit_subject': subject,
            'recent_commit': commit_date[:10] >= '2026-04-22',
            'local_source_path': 'source/' + slug, 'code_file_count': len(code), 'checked_out_files': len(rows),
            'checked_out_bytes': sum(x['bytes'] for x in rows), 'omitted_file_count': len(missing),
            'lfs_pointer_files': lfs, 'submodules': [p for p,v in tree.items() if v['kind']=='commit'],
            'license_files': license_files, 'license_preview': license_preview, 'readme_files': readmes,
            'source_manifest': 'raw_logs/' + slug + '.files.json',
            'source_manifest_sha256': hashlib.sha256(manifest.encode()).hexdigest(),
            'entrypoint_candidates': [p for p in code if re.search(r'(train|eval|demo|play|run|main|planner|controller|mapping|navigation)', p, re.I)][:18],
            'verification': {'git_blob_mismatches': 0, 'tracked_worktree_clean': True,
                             'attribute_converted_files': converted},
            'reproduction_status': 'not_run', 'acquisition_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}


def acquire(repo: dict, verify_only: bool = False) -> dict:
    dst = ROOT/'source'/repo['name'].replace('/', '__')
    log = ROOT/'raw_logs'/(repo['name'].replace('/', '__') + '.acquisition.json')
    try:
        if not (dst/'.git').exists():
            if verify_only:
                raise RuntimeError('Missing checkout')
            git(['clone', '--depth', '1', '--filter=blob:none', '--no-checkout', '--branch', repo['default_branch'], repo['canonical_url'] + '.git', str(dst)])
        if not verify_only:
            pin = repo.get('pinned_commit')
            if pin:
                try:
                    git(['cat-file', '-e', pin + '^{commit}'], dst)
                except RuntimeError:
                    git(['fetch', '--depth', '1', 'origin', pin], dst)
            git(['sparse-checkout', 'init', '--no-cone'], dst)
            (dst/'.git/info/sparse-checkout').write_text('\n'.join(PATTERNS) + '\n')
            git(['checkout', '--detach', pin or 'HEAD'], dst)
        result = inspect(repo, dst)
    except Exception as exc:
        result = {**repo, 'status': 'acquisition_failed', 'error': str(exc), 'local_source_path': str(dst.relative_to(ROOT))}
    log.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'name': repo['name'], 'status': result['status'], 'code_files': result.get('code_file_count'),
                      'recent': result.get('recent_commit'), 'error': result.get('error')}, ensure_ascii=False), flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--restore', action='store_true', help='Restore exact commits from the final manifest')
    args = parser.parse_args()
    for name in ('source', 'raw_logs'):
        (ROOT/name).mkdir(exist_ok=True)
    (ROOT/'raw_logs'/'sparse-patterns.txt').write_text('\n'.join(PATTERNS) + '\n')
    filename = 'repository_manifest.yaml' if args.restore else 'selection.json'
    selected = json.loads((ROOT/filename).read_text())['repositories']
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = list(executor.map(lambda r: acquire(r, args.verify_only), selected))
    output = 'verification_receipts.json' if args.verify_only else ('restoration_acquisition.json' if args.restore else 'acquisition.json')
    (ROOT/'raw_logs'/output).write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    accepted = [r for r in results if r['status'] == 'imported']
    print(json.dumps({'imported': len(accepted), 'recent_commit': sum(r['recent_commit'] for r in accepted),
                      'failed': len(results)-len(accepted)}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
