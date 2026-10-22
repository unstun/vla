"""Lossless, content-verified relocation of one inactive remote archive."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import stat
import subprocess
import time

HERE = Path(__file__).resolve().parent
OUT = HERE / 'results/recovery'
SOURCE = Path('/data/sun/vla_mppi_20261009/mac_archive_20261012')
DEST = Path('/home/sun/vla_exec/relocated_archives/mac_archive_20261012')


def inventory(root):
    rows = []
    for path in sorted(root.rglob('*')):
        info = path.lstat()
        row = dict(path=str(path.relative_to(root)), mode=stat.S_IMODE(info.st_mode))
        if path.is_symlink():
            row.update(kind='symlink', target=os.readlink(path))
        elif path.is_file():
            h = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(8 * 1024**2), b''):
                    h.update(chunk)
            row.update(kind='file', bytes=info.st_size, sha256=h.hexdigest())
        elif path.is_dir():
            row.update(kind='directory')
        else:
            raise RuntimeError(f'Unsupported archive entry: {path}')
        rows.append(row)
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    receipt = OUT / 'archive_relocation.json'
    assert not receipt.exists(), 'Never overwrite a relocation receipt'
    assert SOURCE.is_dir() and not SOURCE.is_symlink() and not DEST.exists()
    assert shutil.disk_usage(DEST.parent.parent).free > 20 * 1024**3
    before = shutil.disk_usage(SOURCE).free
    started = time.time()
    print('Hashing original inactive archive', flush=True)
    original = inventory(SOURCE)
    (OUT / 'archive_inventory.json').write_text(json.dumps(original, indent=2) + '\n')
    DEST.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['rsync', '-a', str(SOURCE) + '/', str(DEST) + '/'], check=True)
    print('Verifying both copies before freeing source bytes', flush=True)
    assert original == inventory(DEST), 'Destination content or mode mismatch'
    assert original == inventory(SOURCE), 'Source changed during transfer'
    backup = SOURCE.with_name(SOURCE.name + '.verified_relocation_source')
    assert not backup.exists()
    SOURCE.rename(backup)
    SOURCE.symlink_to(DEST, target_is_directory=True)
    assert SOURCE.resolve() == DEST.resolve()
    # Only remove the redundant, fully verified copy, never the sole archive.
    shutil.rmtree(backup)
    result = dict(source=str(SOURCE), destination=str(DEST), source_is_symlink=True,
        inventory_sha256=hashlib.sha256((OUT / 'archive_inventory.json').read_bytes()).hexdigest(),
        files=sum(r['kind'] == 'file' for r in original),
        bytes=sum(r.get('bytes', 0) for r in original),
        data_free_before=before, data_free_after=shutil.disk_usage(SOURCE.parent).free,
        started_utc_s=started, finished_utc_s=time.time(), content_verified=True,
        frozen_v283_modified=False, numerical_gates_modified=False)
    receipt.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
