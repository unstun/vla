#!/usr/bin/env python3
"""Phase D.1a on the execution host: the one authorised download of the InteriorAgent scene, verified file by file.

    python3 scripts/phase_d1_fetch_scene.py --manifest setup/phase_d1_interioragent/kujiale_0031_hf_tree.json \
        --dest "$ROOT/scenes/interioragent_ac599fe2"

Authorised by Dr Sun 2026-09-15 (1 download, kujiale_0031, InteriorAgent Terms of Use accepted for this project).
Standard library only (the host has system Python 3.10 and no pip).

1. Re-lists the pinned revision from the HF API and refuses to download if the listing differs from the manifest.
2. Downloads every file into DEST/<scene>.partial/, verifying size and LFS sha256 (or git blob sha1 for non-LFS files).
   Files already in .partial with the right size and hash are kept, so an interrupted fetch resumes instead of
   starting over.
3. Writes download_record.json and SHA256SUMS.txt, then renames .partial to DEST/<scene>. Refuses if that exists.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
import pathlib
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request

UA = {'User-Agent': 'vla-phase-d1-fetch/1.0'}


def utc():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def list_revision(repo, revision, folder):
    url = 'https://huggingface.co/api/datasets/{}/tree/{}/{}?recursive=true'.format(
        repo, revision, urllib.parse.quote(folder))
    out = []
    while url:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
            out += json.load(r)
            link = r.headers.get('Link') or ''
        m = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = m.group(1) if m else None
    return out


def digests(path):
    sha256, sha1 = hashlib.sha256(), hashlib.sha1()
    size = path.stat().st_size
    sha1.update(b'blob %d\0' % size)
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            sha256.update(chunk)
            sha1.update(chunk)
    return size, sha256.hexdigest(), sha1.hexdigest()


def verified(path, entry):
    if not path.is_file():
        return None
    size, sha256, sha1 = digests(path)
    if size != entry['size']:
        return None
    if entry['lfs_sha256'] and sha256 != entry['lfs_sha256']:
        return None
    if not entry['lfs_sha256'] and sha1 != entry['git_oid']:
        return None
    return sha256


def fetch_one(entry, template, partial, attempts=4):
    rel = entry['path'].split('/', 1)[1]
    target = partial / rel
    sha = verified(target, entry)
    if sha:
        return {'path': entry['path'], 'size': entry['size'], 'sha256': sha, 'attempts': 0, 'kept_from_partial': True}
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + '.download')
    url = template.format(path=urllib.parse.quote(entry['path']))
    last = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r, open(tmp, 'wb') as f:
                shutil.copyfileobj(r, f, 1 << 20)
            sha = verified(tmp, entry)
            if sha is None:
                raise ValueError('size or hash mismatch')
            os.replace(tmp, target)
            return {'path': entry['path'], 'size': entry['size'], 'sha256': sha, 'attempts': attempt,
                    'kept_from_partial': False}
        except Exception as exc:  # noqa: BLE001 - retried, then reported per file
            last = '{}: {}'.format(type(exc).__name__, exc)
            time.sleep(2 * attempt)
    tmp.unlink(missing_ok=True)
    return {'path': entry['path'], 'size': entry['size'], 'sha256': None, 'attempts': attempts, 'error': last}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', type=pathlib.Path, required=True)
    ap.add_argument('--dest', type=pathlib.Path, required=True)
    ap.add_argument('--workers', type=int, default=6)
    args = ap.parse_args(argv)
    man = json.loads(args.manifest.read_text())
    scene = man['scene']
    final, partial = args.dest / scene, args.dest / (scene + '.partial')
    if final.exists():
        sys.exit('refusing to overwrite an existing scene copy: {}'.format(final))
    args.dest.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(args.dest).free
    if free < man['bytes'] + 2 * 1024 ** 3:
        sys.exit('only {:.1f} GB free for {:.1f} GB of scene'.format(free / 1024 ** 3, man['bytes'] / 1024 ** 3))

    started = utc()
    live = sorted((e['path'], int(e['size']), (e.get('lfs') or {}).get('oid'), e['oid'])
                  for e in list_revision(man['repo'], man['revision'], scene) if e.get('type') == 'file')
    pinned = sorted((e['path'], e['size'], e['lfs_sha256'], e['git_oid']) for e in man['entries'])
    if live != pinned:
        diff = sorted(set(live) ^ set(pinned))[:10]
        sys.exit('live listing of {}@{} differs from the manifest ({} vs {} files); first differences: {}'.format(
            man['repo'], man['revision'], len(live), len(pinned), diff))
    print('{} listing matches the manifest: {} files, {} bytes'.format(utc(), len(pinned), man['bytes']), flush=True)

    partial.mkdir(exist_ok=True)
    t0 = time.monotonic()
    records, done_bytes = [], 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(fetch_one, e, man['resolve_url_template'], partial) for e in man['entries']]
        for i, fut in enumerate(concurrent.futures.as_completed(futures), 1):
            rec = fut.result()
            records.append(rec)
            done_bytes += rec['size'] if rec['sha256'] else 0
            if i % 50 == 0 or i == len(futures):
                print('{} {}/{} files, {:.1f} MiB verified, {:.0f} s'.format(
                    utc(), i, len(futures), done_bytes / 2 ** 20, time.monotonic() - t0), flush=True)
    records.sort(key=lambda r: r['path'])
    failed = [r for r in records if not r['sha256']]
    record = {
        'repo': man['repo'], 'revision': man['revision'], 'scene': scene, 'manifest': str(args.manifest),
        'manifest_sha256': hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        'started_utc': started, 'finished_utc': utc(), 'seconds': round(time.monotonic() - t0, 1),
        'files': len(records), 'bytes_verified': done_bytes, 'failed': len(failed),
        'kept_from_partial': sum(1 for r in records if r.get('kept_from_partial')), 'records': records,
    }
    (args.dest / (scene + '_download_record.json')).write_text(json.dumps(record, indent=1) + '\n')
    if failed:
        print('PHASE_D1A_FETCH_FAILED failed={} first={}'.format(len(failed), failed[:3]), flush=True)
        return 1
    with open(partial / 'SHA256SUMS.txt', 'w') as f:
        for r in records:
            f.write('{}  {}\n'.format(r['sha256'], r['path'].split('/', 1)[1]))
    os.rename(partial, final)
    print('PHASE_D1A_FETCH_DONE files={} bytes={} seconds={} dest={}'.format(
        len(records), done_bytes, record['seconds'], final), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
