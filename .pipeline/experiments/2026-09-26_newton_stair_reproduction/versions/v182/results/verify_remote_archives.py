"""Verify archive/member bytes on the storage host without extraction."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import time

p = argparse.ArgumentParser()
p.add_argument('--archives', type=Path, required=True)
p.add_argument('--receipts', type=Path, required=True)
a = p.parse_args()
a.receipts.mkdir(parents=True, exist_ok=True)
for record in sorted(a.archives.glob('v182_*.json')):
    data = json.loads(record.read_text())
    archive = a.archives / data['archive']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == data['archive_sha256']
    with tarfile.open(archive) as bundle:
        members = {m.name: m for m in bundle if m.isfile()}
        assert set(members) == set(data['files'])
        for name, expected in data['files'].items():
            raw = bundle.extractfile(members[name]).read()
            assert len(raw) == expected['bytes']
            assert hashlib.sha256(raw).hexdigest() == expected['sha256']
    data.update(remote_verified=True, remote_host='gpu5070ti',
                remote_archive=str(archive.resolve()), verified_epoch=time.time())
    (a.receipts / record.name).write_text(json.dumps(data, indent=2) + '\n')
    print(data['run'], 'ARCHIVE_AND_ALL_MEMBERS_PASS', flush=True)
