"""Verify native overlay and recovery-evidence TAR members without extraction."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys
import tarfile


def digest(stream):
    return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    root = Path(sys.argv[1])
    results = {}
    for name in ('overlay_archive_manifest.json', 'resume_evidence_archive_manifest.json'):
        manifest = json.loads((root / name).read_text())
        path = root / manifest['archive_name']
        assert path.stat().st_size == manifest['archive_bytes']
        with path.open('rb') as stream:
            assert digest(stream) == manifest['archive_sha256']
        with tarfile.open(path) as tf:
            members = tf.getmembers()
            assert len(members) == len({m.name for m in members})
            assert all(m.isfile() or m.isdir() or m.issym() for m in members)
            assert {m.name for m in members if m.isfile()} == set(manifest['files'])
            assert {m.name: m.linkname for m in members if m.issym()} == manifest['symlinks']
            for member, expected in manifest['files'].items():
                assert tf.getmember(member).size == expected['bytes'], member
                with tf.extractfile(member) as stream:
                    assert digest(stream) == expected['sha256'], member
        results[manifest['archive_name']] = dict(verified=True, archive_sha256=manifest['archive_sha256'],
                                               archive_bytes=manifest['archive_bytes'],
                                               files_verified=len(manifest['files']),
                                               symlinks_verified=len(manifest['symlinks']))
    result = dict(verified=True, archives=results, verification_utc=datetime.now(timezone.utc).isoformat())
    (root / 'extra_archives_verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
