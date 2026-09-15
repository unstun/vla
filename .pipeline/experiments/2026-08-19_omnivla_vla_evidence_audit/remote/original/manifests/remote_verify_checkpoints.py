#!/usr/bin/env python3
"""Verify remote checkpoint bytes against the tracked pinned manifest.

This verifier is read-only: it does not rewrite the tracked manifest or any
checkpoint.  It understands the two digest kinds used by the manifest and
prints one tab-separated result per selected file followed by a summary.
"""

import argparse
import csv
import hashlib
from pathlib import Path
import sys


def content_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha1(path: Path, size: int) -> str:
    digest = hashlib.sha1()
    digest.update(f"blob {size}\0".encode("ascii"))
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--checkpoint-root", required=True, type=Path)
    parser.add_argument(
        "--repo-prefix",
        default="NHirose/",
        help="verify only manifest rows whose repo starts with this value",
    )
    args = parser.parse_args()

    ok = 0
    absent = 0
    mismatched = 0
    with args.manifest.open(newline="", encoding="utf-8") as stream:
        rows = csv.DictReader(stream, delimiter="\t")
        for row in rows:
            if not row["repo"].startswith(args.repo_prefix):
                continue
            relative = Path(row["local_path"])
            try:
                relative = relative.relative_to("checkpoints")
            except ValueError:
                print(f"INVALID_PATH\t{row['local_path']}")
                mismatched += 1
                continue
            path = args.checkpoint_root / relative
            if not path.is_file():
                print(f"ABSENT\t{row['repo']}\t{row['file']}\t{path}")
                absent += 1
                continue
            expected_size = int(row["size_bytes"])
            actual_size = path.stat().st_size
            if row["sha256_kind"] == "git-blob-sha1":
                actual_digest = git_blob_sha1(path, actual_size)
            elif row["sha256_kind"] in {"lfs-sha256", "url-embedded-sha256"}:
                actual_digest = content_sha256(path)
            else:
                print(f"UNKNOWN_KIND\t{row['repo']}\t{row['file']}\t{row['sha256_kind']}")
                mismatched += 1
                continue
            status = "OK"
            if actual_size != expected_size or actual_digest != row["sha256"]:
                status = "MISMATCH"
                mismatched += 1
            else:
                ok += 1
            print(
                "\t".join(
                    [
                        status,
                        row["repo"],
                        row["revision"],
                        row["file"],
                        str(actual_size),
                        actual_digest,
                    ]
                )
            )
    print(f"SUMMARY\tok={ok}\tabsent={absent}\tmismatched={mismatched}")
    return 0 if absent == 0 and mismatched == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
