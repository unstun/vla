"""Verify a non-pruning snapshot after both owned execution containers exit."""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
PREFIX = Path('/data/sun/vla_mppi_20261009')
TASK = PREFIX / 'trials/v282_A04_attempt01'
RAW = TASK / 'runs/v282_A04_attempt01'


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 2**20), b''):
            result.update(block)
    return result.hexdigest()


def main():
    (HERE/'results').mkdir(exist_ok=True)
    process = json.loads((RAW / 'process.json').read_text())
    assert process['finished_utc'] and isinstance(process['exit_code'], int)
    execution = json.loads(EXECUTION.read_text())
    assert isinstance(execution['process_exit_code'], int)
    names = subprocess.check_output(['docker', 'ps', '--format', '{{.Names}}'], text=True).splitlines()
    assert not any(name in names for name in ('v241-host-route01', 'v282-a04-attempt01'))
    manifest=RAW/'raw_capture_manifest.json'
    if manifest.exists() and (RAW/'raw_capture.zip').exists():
        rows=json.loads(manifest.read_text())['members'];archive=RAW/'raw_capture.zip'
        with zipfile.ZipFile(archive) as zipped:
            for name,row in rows.items():
                result=hashlib.sha256();size=0
                with zipped.open(name) as stream:
                    for block in iter(lambda:stream.read(4*2**20),b''):result.update(block);size+=len(block)
                assert size==row['bytes'] and result.hexdigest()==row['sha256'],name
                if (RAW/name).exists():assert digest(RAW/name)==row['sha256'],name
        report=dict(passed=True,originals_pruned=True,archive=str(archive),archive_bytes=archive.stat().st_size,
            archive_sha256=digest(archive),members=rows,process=process,outer_runtime_completed=True,
            claim='Original recorder retention archive verified after own execution exit; no new pruning.')
        (HERE/'results/capture_snapshot.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:report[k] for k in ('passed','archive_bytes','archive_sha256')}),flush=True)
        return
    paths = sorted(p for p in RAW.rglob('*') if p.is_file())
    rows = {str(p.relative_to(RAW)): dict(bytes=p.stat().st_size, sha256=digest(p)) for p in paths}
    archive = TASK / 'capture_snapshot.zip'
    if not archive.exists():
        with zipfile.ZipFile(archive, 'x', allowZip64=True) as output:
            for path in paths:
                compression = zipfile.ZIP_STORED if path.suffix in ('.zip', '.npz') else zipfile.ZIP_DEFLATED
                output.write(path, str(path.relative_to(RAW)), compress_type=compression, compresslevel=3)
    with zipfile.ZipFile(archive) as output:
        assert set(output.namelist()) == set(rows)
        for name, row in rows.items():
            result = hashlib.sha256()
            size = 0
            with output.open(name) as stream:
                for block in iter(lambda: stream.read(4 * 2**20), b''):
                    result.update(block)
                    size += len(block)
            assert size == row['bytes'] and result.hexdigest() == row['sha256'], name
            assert digest(RAW / name) == row['sha256'], name
    report = dict(passed=True, originals_pruned=False, original_files_retained=True,
        archive=str(archive), archive_bytes=archive.stat().st_size, archive_sha256=digest(archive),
        members=rows, process=process, outer_runtime_completed=True,
        claim='Verified non-pruning snapshot after both owned containers exit. Source PIDs belong to the private namespace, not host peers.')
    (HERE / 'results/capture_snapshot.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('passed', 'archive_bytes', 'archive_sha256')}), flush=True)


if __name__ == '__main__':
    main()
