"""Verify the failed trial TAR and every original member inside its raw ZIP."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import zipfile


def digest(stream):
    value = hashlib.sha256()
    for data in iter(lambda: stream.read(4 * 1024**2), b''):
        value.update(data)
    return value.hexdigest()


def main():
    root = Path(sys.argv[1])
    manifest = json.loads((root / 'trial_archive_manifest.json').read_text())
    archive = root / manifest['archive_name']
    assert archive.stat().st_size == manifest['archive_bytes']
    with archive.open('rb') as stream:
        assert digest(stream) == manifest['archive_sha256']
    with tarfile.open(archive) as bundle:
        names = {m.name for m in bundle.getmembers() if m.isfile()}
        assert names == set(manifest['files'])
        for name, expected in manifest['files'].items():
            member = bundle.getmember(name)
            assert member.size == expected['bytes'], name
            with bundle.extractfile(member) as stream:
                assert digest(stream) == expected['sha256'], name
        prefix = 'v192_mac_full_attempt01/runs/v192_mac_full_attempt01/'
        raw = json.load(bundle.extractfile(prefix + 'raw_capture_manifest.json'))
        with zipfile.ZipFile(bundle.extractfile(prefix + 'raw_capture.zip')) as capture:
            assert set(capture.namelist()) == set(raw['members'])
            for name, expected in raw['members'].items():
                assert capture.getinfo(name).file_size == expected['bytes'], name
                with capture.open(name) as stream:
                    assert digest(stream) == expected['sha256'], name
    result = {'verified': True, 'archive_sha256': manifest['archive_sha256'],
              'archive_bytes': archive.stat().st_size, 'outer_files_verified': len(names),
              'raw_zip_members_verified': len(raw['members']),
              'terminal_status': 'FAILED', 'route_arrived': False,
              'review_video_created': False}
    (root / 'remote_verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
