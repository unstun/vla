#!/usr/bin/env python3
"""Copy, hash-verify, then relocate only the explicit reference-source inventory."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import subprocess

HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE/'plan.json').read_text())
PROJECT = Path(PLAN['project'])
DEST = Path(PLAN['destination'])
RAW = HERE/'raw_logs'


def volume() -> None:
    data = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/ModelArchive']))
    assert data['VolumeUUID']==PLAN['volume_uuid'] and not data['Internal'] and data['Writable']
    assert data['MountPoint']=='/Volumes/ModelArchive'


def fingerprint(root: Path, with_hash: bool = True) -> dict:
    result = {}
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            p = Path(base)/name
            s = p.lstat()
            rel = str(p.relative_to(root))
            if p.is_symlink():
                row = {'kind':'symlink','target':os.readlink(p)}
            elif p.is_dir():
                row = {'kind':'directory','mode':stat.S_IMODE(s.st_mode)}
            else:
                row = {'kind':'file','bytes':s.st_size,'mode':stat.S_IMODE(s.st_mode)}
                if with_hash:
                    h=hashlib.sha256()
                    with p.open('rb') as f:
                        for chunk in iter(lambda:f.read(4*1024*1024), b''):
                            h.update(chunk)
                    row['sha256']=h.hexdigest()
                else:
                    row['mtime_ns']=s.st_mtime_ns
            result[rel]=row
    return result


def slug(item: dict) -> str:
    return item['relative_path'].replace('/','__')


def copy_one(item: dict) -> dict:
    src = PROJECT/item['relative_path']
    dst = DEST/item['relative_path']
    assert src.is_dir() and not src.is_symlink()
    assert not dst.exists(), f'Destination already exists: {dst}'
    before = fingerprint(src, False)
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ditto','--noqtn',str(src),str(dst)], check=True)
    left = fingerprint(src)
    right = fingerprint(dst)
    after = fingerprint(src,False)
    assert before==after, f'Source changed while copying: {src}'
    assert left==right, f'Copied content mismatch: {src}'
    payload=json.dumps(left,sort_keys=True,ensure_ascii=False,indent=2)+'\n'
    key=slug(item)
    (RAW/(key+'.sha256.json')).write_text(payload)
    (RAW/(key+'.source-stat.json')).write_text(json.dumps(after,sort_keys=True))
    receipt={**item,'destination':str(dst),'entries_verified':len(left),
             'file_count':sum(v['kind']=='file' for v in left.values()),
             'bytes_verified':sum(v.get('bytes',0) for v in left.values()),
             'manifest_sha256':hashlib.sha256(payload.encode()).hexdigest(),
             'manifest_path':'raw_logs/'+key+'.sha256.json','status':'copied_and_hash_verified'}
    (RAW/(key+'.receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'copied':item['relative_path'],'files':receipt['file_count'],'bytes':receipt['bytes_verified']}),flush=True)
    return receipt


def switch_all() -> None:
    volume()
    receipts=json.loads((HERE/'copy_receipts.json').read_text())
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=PROJECT).decode().split('\0')
    for row in receipts:
        src=PROJECT/row['relative_path']; dst=Path(row['destination']); key=slug(row)
        assert dst==DEST/row['relative_path'] and dst.is_dir() and not dst.is_symlink()
        if row['mode']=='copy_only_tracked_snapshot':
            row['status']='external_copy_verified_local_git_snapshot_retained'
            continue
        assert not any(p.startswith(row['relative_path']+'/') for p in tracked)
        if src.is_symlink():
            assert src.resolve()==dst.resolve()
            row['status']='external_link_verified_internal_original_removed'
            continue
        assert src.is_dir() and not src.is_symlink()
        before=json.loads((RAW/(key+'.source-stat.json')).read_text())
        assert fingerprint(src,False)==before, f'Source changed after verification: {src}'
        expected=json.loads((RAW/(key+'.sha256.json')).read_text())
        assert fingerprint(dst)==expected, f'External copy changed: {dst}'
        volume()
        backup=src.with_name(src.name+'.internal-migration-20261022')
        assert not backup.exists() and not backup.is_symlink()
        src.rename(backup)
        try:
            src.symlink_to(dst,target_is_directory=True)
            assert src.is_symlink() and src.resolve()==dst.resolve()
            assert fingerprint(backup,False)==before
            # Delete only this renamed original, after independent copy verification.
            assert backup.parent==src.parent and backup.name.endswith('.internal-migration-20261022')
            shutil.rmtree(backup)
        except BaseException:
            if backup.exists():
                if src.is_symlink():src.unlink()
                if not src.exists():backup.rename(src)
            raise
        row['status']='external_link_verified_internal_original_removed'
        (HERE/'migration_receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'moved':row['relative_path'],'bytes':row['bytes_verified']}),flush=True)
    (HERE/'migration_receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['copy','switch','relink'])
    args=parser.parse_args()
    RAW.mkdir(exist_ok=True)
    volume()
    if args.phase=='copy':
        assert not DEST.exists(), 'Use a new destination; never merge into existing storage.'
        DEST.mkdir(parents=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            receipts=list(pool.map(copy_one,PLAN['items']))
        (HERE/'copy_receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')
    elif args.phase=='switch':
        switch_all()
    else:
        for item in PLAN['items']:
            if item['mode']!='move_to_external':
                continue
            src=PROJECT/item['relative_path'];dst=DEST/item['relative_path']
            assert dst.is_dir()
            if src.is_symlink():
                assert src.resolve()==dst.resolve()
                continue
            assert not src.exists(), f'Refusing to replace existing content: {src}'
            src.parent.mkdir(parents=True,exist_ok=True)
            src.symlink_to(dst,target_is_directory=True)


if __name__=='__main__':
    main()
