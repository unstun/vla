"""Archive closed captures without deleting originals; verify member bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_archive(archive, files):
    with tarfile.open(archive) as bundle:
        members = {m.name: m for m in bundle if m.isfile()}
        if set(members) != set(files):
            raise ValueError("Archive file set mismatch")
        for name, item in files.items():
            data = bundle.extractfile(members[name]).read()
            if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError("Archive member mismatch: " + name)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    for run in sorted(a.runs.iterdir()):
        if not (run / "process.json").exists() or not (run / "result.json").exists():
            continue
        receipt_path = a.output / (run.name + ".json")
        if receipt_path.exists():
            old = json.loads(receipt_path.read_text())
            if digest(a.output / old["archive"]) != old["archive_sha256"]:
                raise ValueError("Existing archive changed")
            continue
        process = json.loads((run / "process.json").read_text())
        if "finished_utc" not in process:
            raise ValueError("Unclosed process")
        files = {str(p.relative_to(run)): dict(bytes=p.stat().st_size, sha256=digest(p))
                 for p in sorted(run.rglob("*")) if p.is_file()}
        archive = a.output / (run.name + ".tar.gz")
        with tarfile.open(archive, "x:gz") as bundle:
            for name in files:
                bundle.add(run / name, arcname=name, recursive=False)
        verify_archive(archive, files)
        receipt = dict(run=run.name, source=str(run), archive=archive.name,
                       archive_sha256=digest(archive), archive_bytes=archive.stat().st_size,
                       files=files, remote_verified=False)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
        print(run.name, len(files), archive.stat().st_size, flush=True)


if __name__ == "__main__":
    main()
