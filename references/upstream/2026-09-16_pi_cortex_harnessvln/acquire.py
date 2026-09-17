"""Acquire exact selected upstream commits without running upstream code."""

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
REPOS = [
    ("pi", "earendil-works/pi", "d981de1229ef899957bbe968bc8dcda02a21f477"),
    ("emos", "automatika-robotics/emos", "31b82958e7a1646b9af606184518333c97290f58"),
    ("embodied-agents", "automatika-robotics/embodied-agents", "c37ab75db4aba88bcc99d17f6eabac146ad46d20"),
]


def main():
    records = []
    for name, repo, commit in REPOS:
        target = ROOT / "source" / name
        target.mkdir(parents=True, exist_ok=True)
        log_path = ROOT / "raw_logs" / f"{name}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a") as log:
            def git(*args):
                log.write(f"git {' '.join(args)}\n")
                log.flush()
                result = subprocess.run(["git", *args], cwd=target, check=True,
                                        stdout=subprocess.PIPE, stderr=log, text=True)
                log.write(result.stdout)
                return result.stdout.strip()

            url = f"https://github.com/{repo}.git"
            if not (target / ".git").exists():
                git("init")
                git("remote", "add", "origin", url)
                git("fetch", "--depth=1", "origin", commit)
                git("checkout", "--detach", "FETCH_HEAD")
            if git("rev-parse", "HEAD") != commit or git("status", "--porcelain"):
                raise RuntimeError(f"Refusing changed or mismatched source: {target}")
            records.append({"name": name, "url": url, "commit": commit,
                            "tree": git("rev-parse", "HEAD^{tree}"),
                            "source": str(target.relative_to(ROOT)),
                            "submodules": git("submodule", "status").splitlines(),
                            "status": "imported_reference_snapshot", "runtime_run": False})
        hashes = {}
        for file in sorted(target.rglob("*")):
            if file.is_file() and ".git" not in file.relative_to(target).parts:
                hashes[str(file.relative_to(target))] = hashlib.sha256(file.read_bytes()).hexdigest()
        manifest = ROOT / f"{name}_sha256.json"
        manifest.write_text(json.dumps(hashes, indent=2) + "\n")
        records[-1]["file_count"] = len(hashes)
        records[-1]["hash_manifest"] = manifest.name
        print(f"Acquired {name} {commit}: {len(hashes)} files", flush=True)
    (ROOT / "acquisition.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
