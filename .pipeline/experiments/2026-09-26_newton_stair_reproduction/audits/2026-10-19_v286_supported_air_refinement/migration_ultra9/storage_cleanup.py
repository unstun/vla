"""Review or execute an exact image/download-cache cleanup, never run-data cleanup."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time

ROOT = Path('/home/ubuntu/sun/vla_v286_20261020')
IMAGE = 'sha256:ebd660bc59a0a27901d3a002a4666cf73b310e61b170f1a927e68c6bbcbb6f38'
CACHES = [Path(p) for p in ['/home/ubuntu/anaconda3/pkgs', '/home/ubuntu/miniconda3/pkgs',
    '/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda/conda_pkgs',
    '/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda/conda_pkgs_main']]


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024**2), b''):
            value.update(block)
    return value.hexdigest()


def image_state():
    item = json.loads(subprocess.check_output(['docker', 'image', 'inspect', IMAGE], text=True))[0]
    assert item['Id'] == IMAGE
    assert not subprocess.check_output(['docker', 'ps', '-a', '--filter', 'ancestor=' + IMAGE,
        '--format', '{{.ID}}'], text=True).strip(), 'Image has a container reference'
    assert len(item['RepoDigests']) == 1 and item['RepoDigests'][0].endswith('@' + IMAGE)
    return dict(id=IMAGE, tags=item['RepoTags'], restore_digest=item['RepoDigests'][0],
        reported_image_bytes=item['Size'], created=item['Created'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute-plan-sha256')
    args = parser.parse_args()
    plan_path = ROOT / 'evidence/storage_cleanup_plan01.json'
    if not args.execute_plan_sha256:
        assert not plan_path.exists()
        files = []
        for directory in CACHES:
            assert directory.is_dir() and not directory.is_symlink()
            for path in sorted(directory.iterdir()):
                if path.is_symlink() or not path.is_file() or not path.name.endswith(('.conda', '.tar.bz2')):
                    continue
                info = path.stat()
                files.append(dict(path=str(path), bytes=info.st_size, sha256=sha(path)))
        report = dict(stage='review_only', created_utc_s=time.time(), image=image_state(), files=files,
            download_cache_bytes=sum(f['bytes'] for f in files), free_bytes=shutil.disk_usage(ROOT).free,
            image_accounting_note='Docker system-df and image-inspect sizes differ; verify actual free-space delta after removal.',
            retained='All models, teacher banks, experiment archives, videos, installed environments, other user data and the active Foxy image')
        with plan_path.open('x') as out:
            json.dump(report, out, indent=2)
        print(json.dumps(dict(plan=str(plan_path), plan_sha256=sha(plan_path), image=report['image'],
            cache_files=len(files), download_cache_bytes=report['download_cache_bytes'], destructive_actions=0)))
        return
    assert sha(plan_path) == args.execute_plan_sha256
    plan = json.loads(plan_path.read_text())
    assert image_state() == plan['image']
    targets = {f['path'] for f in plan['files']}
    for row in plan['files']:
        path = Path(row['path'])
        assert path.parent in CACHES and not path.is_symlink()
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal():
            continue
        try:
            for fd in (proc / 'fd').iterdir():
                try:
                    assert os.readlink(fd) not in targets, ('Open download archive', proc.name, fd)
                except OSError:
                    pass
        except OSError:
            pass
    receipt = ROOT / 'evidence/storage_cleanup_execution01.json'
    assert not receipt.exists()
    report = dict(started_utc_s=time.time(), plan_sha256=args.execute_plan_sha256,
        authorization='Explicit user approval of reviewed image and download archives',
        free_bytes_before=shutil.disk_usage(ROOT).free, removed_files=[])
    receipt.write_text(json.dumps(report, indent=2) + '\n')
    result = subprocess.run(['docker', 'image', 'rm', IMAGE], capture_output=True, text=True)
    report['image_removal'] = dict(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
    receipt.write_text(json.dumps(report, indent=2) + '\n')
    result.check_returncode()
    for row in plan['files']:
        Path(row['path']).unlink()
        report['removed_files'].append(row)
    report.update(finished_utc_s=time.time(), free_bytes_after=shutil.disk_usage(ROOT).free,
        models_or_experiments_removed=False, installed_environments_changed=False)
    receipt.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'removed_files'}))


if __name__ == '__main__':
    main()
