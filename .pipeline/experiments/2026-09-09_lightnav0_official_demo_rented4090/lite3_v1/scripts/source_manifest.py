"""Create or verify the exact local-to-remote Lite3 source/input sync gate."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exp", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        data = json.loads(args.manifest.read_text())
        bad = []
        for name, expected in data["files"].items():
            path = args.exp / name
            if not path.is_file() or digest(path) != expected:
                bad.append(name)
        print(json.dumps({"checked": len(data["files"]), "mismatches": bad,
                          "passed": not bad}, indent=2))
        raise SystemExit(bool(bad))
    files = {}
    for directory in ("work/LightNav-0-lite3-v1", "lite3_v1/assets", "lite3_v1/policy",
                      "lite3_v1/scripts", "lite3_v1/source"):
        for path in sorted((args.exp / directory).rglob("*")):
            if not path.is_file() or any(part in ("__pycache__", ".pytest_cache", ".ruff_cache")
                                         for part in path.parts):
                continue
            files[str(path.relative_to(args.exp))] = digest(path)
    args.manifest.write_text(json.dumps({"files": files, "count": len(files)}, indent=2)+"\n")
    print(json.dumps({"file_count": len(files), "manifest": str(args.manifest)}))


if __name__ == "__main__":
    main()
