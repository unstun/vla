"""Verify and unpack a captured dependency into a task/container-local path."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unpack(wheel, manifest_path, destination):
    manifest = json.loads(manifest_path.read_text())
    if sha(wheel) != manifest["sha256"] or wheel.stat().st_size != manifest["bytes"]:
        raise ValueError("foreground dependency wheel identity mismatch")
    if destination.exists():
        raise FileExistsError(destination)
    with zipfile.ZipFile(wheel) as archive:
        expected = manifest["wheel_members_sha256"]
        actual_names = {n for n in archive.namelist() if not n.endswith("/")}
        if actual_names != set(expected):
            raise ValueError("wheel file set differs from captured manifest")
        for name in actual_names:
            relative = PurePosixPath(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("invalid wheel member path")
            payload = archive.read(name)
            if hashlib.sha256(payload).hexdigest() != expected[name]:
                raise ValueError("wheel member hash mismatch: " + name)
            path = destination.joinpath(*relative.parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
    return {"wheel_sha256": manifest["sha256"], "files": len(expected),
            "unpacked_hashes_match": all(sha(destination / n) == h for n, h in expected.items())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    result = unpack(args.wheel, args.manifest, args.destination)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
