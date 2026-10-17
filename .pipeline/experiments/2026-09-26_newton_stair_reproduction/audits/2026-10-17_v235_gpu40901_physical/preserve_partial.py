"""Make a verified non-pruning snapshot after the owned process group exits."""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
RAW = Path('/home/ubuntu/sun/vla_v234_20261017/trials/v235_linux_full_attempt01/runs/v235_linux_full_attempt01')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    process = json.loads((RAW / 'process.json').read_text())
    assert process['finished_utc'] and process['exit_code'] != 0
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal():
            continue
        try:
            stat = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
        except OSError:
            continue
        assert int(stat[2]) != process['pgid'], 'Owned recorder process group is still alive'
    containers = subprocess.check_output(['docker', 'ps', '--format', '{{.Names}}'], text=True).splitlines()
    assert 'v235-linux-full-attempt01' not in containers
    paths = sorted(p for p in RAW.rglob('*') if p.is_file())
    original = {str(p.relative_to(RAW)): dict(bytes=p.stat().st_size, sha256=sha(p)) for p in paths}
    archive = RAW.parent.parent / 'capture_snapshot.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as output:
        for path in paths:
            output.write(path, str(path.relative_to(RAW)))
    with zipfile.ZipFile(archive) as output:
        for name, item in original.items():
            data = output.read(name)
            assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
            assert sha(RAW / name) == item['sha256']
    report = dict(passed=True, original_files_retained=True, originals_pruned=False,
        archive=str(archive), archive_bytes=archive.stat().st_size, archive_sha256=sha(archive),
        members=original, process=process,
        claim='Non-pruning immutable snapshot; original retention lsof failure is preserved. No lsof gate bypass or deletion.')
    (HERE / 'results/capture_snapshot.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('passed', 'archive_bytes', 'archive_sha256')}), flush=True)


if __name__ == '__main__':
    main()
