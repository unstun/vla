"""Verify the exact frozen v197 source/provenance archive on its storage host."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys
import tarfile


def main():
    root = Path(sys.argv[1])
    path = root/'v197_source_archive_manifest.json'
    manifest = json.loads(path.read_text())
    archive = root/manifest['archive_name']
    assert archive.stat().st_size == manifest['archive_bytes']
    with archive.open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==manifest['archive_sha256']
    with tarfile.open(archive) as tf:
        members=tf.getmembers()
        assert len(members)==len({m.name for m in members})==len(manifest['files'])
        assert all(m.isfile() for m in members)
        assert {m.name for m in members}==set(manifest['files'])
        for name,expected in manifest['files'].items():
            assert tf.getmember(name).size==expected['bytes']
            with tf.extractfile(name) as stream:
                assert hashlib.file_digest(stream,'sha256').hexdigest()==expected['sha256'],name
    result=dict(verified=True,archive_sha256=manifest['archive_sha256'],archive_bytes=manifest['archive_bytes'],
                files_verified=len(manifest['files']),display_manifest_sha256=manifest['display_manifest_sha256'],
                verification_utc=datetime.now(timezone.utc).isoformat(),
                archive_manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (root/'v197_source_archive_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
