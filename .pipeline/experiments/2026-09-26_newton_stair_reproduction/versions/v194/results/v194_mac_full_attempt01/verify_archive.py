"""Verify the closed trial TAR, symlinks and every original raw ZIP member."""
from datetime import datetime, timezone
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
    manifest_path = root / 'trial_archive_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    archive = root / manifest['archive_name']
    assert archive.stat().st_size == manifest['archive_bytes']
    with archive.open('rb') as stream:
        assert digest(stream) == manifest['archive_sha256']
    with tarfile.open(archive) as bundle:
        members = bundle.getmembers()
        assert len({m.name for m in members}) == len(members), 'Duplicate TAR member'
        names = {m.name for m in members if m.isfile()}
        symlinks = {m.name: m.linkname for m in members if m.issym()}
        assert names == set(manifest['files'])
        assert symlinks == manifest['symlinks']
        assert all(m.isfile() or m.isdir() or m.issym() for m in members)
        for name, expected in manifest['files'].items():
            member = bundle.getmember(name)
            assert member.size == expected['bytes'], name
            with bundle.extractfile(member) as stream:
                assert digest(stream) == expected['sha256'], name
        prefix = manifest['run'] + '/runs/' + manifest['run'] + '/'
        raw = json.load(bundle.extractfile(prefix + 'raw_capture_manifest.json'))
        with zipfile.ZipFile(bundle.extractfile(prefix + 'raw_capture.zip')) as capture:
            assert len(capture.namelist()) == len(set(capture.namelist()))
            assert set(capture.namelist()) == set(raw['members'])
            for name, expected in raw['members'].items():
                assert capture.getinfo(name).file_size == expected['bytes'], name
                with capture.open(name) as stream:
                    assert digest(stream) == expected['sha256'], name
            driver_name = 'artifacts/stair_driver_result.json'
            if prefix + driver_name in names:
                driver = json.load(bundle.extractfile(prefix + driver_name))
            else:
                driver = json.loads(capture.read(driver_name))
            assert driver['route_arrived'] == manifest['route_arrived']
            assert driver['execution_completed']
        result = json.load(bundle.extractfile(prefix + 'result.json'))
        assert result['finish_request']['backend_terminal_status'] == manifest['terminal_status']
    gate_path = root / 'full_route_verification.json'
    assert hashlib.sha256(gate_path.read_bytes()).hexdigest() == manifest['full_route_verification_sha256']
    assert json.loads(gate_path.read_text())['passed'] == manifest['full_route_gate_passed']
    result = dict(
        verified=True, run=manifest['run'], archive_sha256=manifest['archive_sha256'],
        archive_bytes=archive.stat().st_size, outer_files_verified=len(names),
        symlinks_verified=len(symlinks), raw_zip_members_verified=len(raw['members']),
        terminal_status=manifest['terminal_status'], route_arrived=manifest['route_arrived'],
        full_route_gate_passed=manifest['full_route_gate_passed'],
        verification_utc=datetime.now(timezone.utc).isoformat(),
        verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest())
    (root / 'remote_verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
