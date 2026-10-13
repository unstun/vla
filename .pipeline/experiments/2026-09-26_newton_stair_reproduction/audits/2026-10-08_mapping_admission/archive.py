"""Archive closed owned component evidence, verify every member, then upload."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import tarfile


HERE = Path(__file__).resolve().parent


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.task_root.resolve(strict=True)
    assert root.name.startswith("vla_mapping_admission_attempt02_")
    active = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"], text=True)
    assert not any(name.startswith(("vla-v84-", "vla-v85-")) for name in active.splitlines())
    selected = ["capture_prefix.zip", "prepared_inputs", "results", "workspace/src", "workspace/install",
                "workspace/v84_probe/admission_probe", "workspace/v84_probe/transient_probe",
                "workspace/v85_probe/lane_probe"]
    files = {}
    for name in selected:
        path = root / name
        assert path.exists(), path
        for member in ([path] if path.is_file() else sorted(path.rglob("*"))):
            if member.is_file():
                assert member.resolve().is_relative_to(root), member
                files[str(member.relative_to(root))] = {"bytes": member.stat().st_size, "sha256": sha(member)}
    archive = root / "component_evidence.tar.gz"
    assert not archive.exists()
    with tarfile.open(archive, "w:gz", dereference=True) as output:
        for name in files:
            output.add(root / name, arcname=name, recursive=False)
    with tarfile.open(archive, "r:gz") as check:
        assert set(check.getnames()) == set(files)
        for name, expected in files.items():
            stream = check.extractfile(name)
            assert stream is not None
            digest = hashlib.sha256()
            size = 0
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
            assert size == expected["bytes"] and digest.hexdigest() == expected["sha256"], name
    remote = "/home/sun/vla_artifacts/2026-10-08_mapping_admission/attempt02"
    manifest = {"status": "local_archive_verified", "archive": {"name": archive.name,
                "bytes": archive.stat().st_size, "sha256": sha(archive)}, "members": files,
                "remote_host": "gpu5070ti", "remote_root": remote, "gpu_job_started": False,
                "restore": "Fetch component_evidence.tar.gz from remote_root, verify archive and member hashes, extract to a new task root mounted as /task in the pinned image. Use v84/execute_local.py with a new output attempt or rebuild using the frozen scripts. Never overwrite recorded outputs."}
    local = root / "storage_manifest.json"
    local.write_text(json.dumps(manifest, indent=2) + "\n")
    (HERE / "storage_manifest.json").write_bytes(local.read_bytes())
    create = "from pathlib import Path; p=Path(" + repr(remote) + "); p.mkdir(parents=True,exist_ok=False)"
    subprocess.run(["ssh", "-o", "BatchMode=yes", "gpu5070ti", "python3", "-c", __import__("shlex").quote(create)], check=True)
    subprocess.run(["rsync", "-a", "--", str(archive), str(local), "gpu5070ti:" + remote + "/"], check=True)
    verify = """from pathlib import Path
import hashlib,json,tarfile
p=Path(REMOTE)
m=json.loads((p/'storage_manifest.json').read_text())
def hash_stream(stream):
 d=hashlib.sha256(); size=0
 for chunk in iter(lambda:stream.read(1048576),b''): d.update(chunk);size+=len(chunk)
 return size,d.hexdigest()
a=p/m['archive']['name']
with a.open('rb') as stream: size,digest=hash_stream(stream)
assert size==m['archive']['bytes'] and digest==m['archive']['sha256']
with tarfile.open(a,'r:gz') as archive:
 assert set(archive.getnames())==set(m['members'])
 for name,expected in m['members'].items():
  size,digest=hash_stream(archive.extractfile(name))
  assert size==expected['bytes'] and digest==expected['sha256'],name
print(json.dumps({'passed':True,'archive_sha256':m['archive']['sha256'],'archive_bytes':a.stat().st_size,'members':len(m['members']),'member_bytes':sum(x['bytes'] for x in m['members'].values()),'gpu_job_started':False}))
""".replace("REMOTE", repr(remote))
    result = subprocess.run(["ssh", "-o", "BatchMode=yes", "gpu5070ti", "python3"],
                            input=verify, text=True, capture_output=True, check=True)
    receipt = json.loads(result.stdout)
    receipt.update(remote_root=remote, local_temporary_root=str(root),
                   manifest_sha256=sha(local), owned_containers_closed=True)
    (HERE / "remote_verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
