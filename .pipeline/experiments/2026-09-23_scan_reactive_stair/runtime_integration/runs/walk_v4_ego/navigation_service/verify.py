import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[3]


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_command(name, argv, cwd=ROOT):
    started = time.time()
    proc = subprocess.run(
        argv,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    elapsed = time.time() - started
    return {
        "name": name,
        "argv": argv,
        "returncode": proc.returncode,
        "elapsed_s": elapsed,
        "output": proc.stdout,
    }


def main():
    checks_dir = ROOT / "checks" / time.strftime("checks_%Y%m%dT%H%M%SZ", time.gmtime())
    checks_dir.mkdir(parents=True, exist_ok=False)
    commands = [
        ("compileall", [sys.executable, "-m", "compileall", "-q", "core.py", "test_core.py", "verify.py"], ROOT),
        ("unittest", [sys.executable, "-m", "unittest", "-v", "test_core.py"], ROOT),
        (
            "lead_adversarial",
            [
                sys.executable,
                ".trellis/tasks/09-16-emos-harnessvln-reimplementation/research/acceptance/test_p2a_adversarial.py",
            ],
            REPO_ROOT,
        ),
    ]
    results = []
    for index, (name, argv, cwd) in enumerate(commands):
        result = run_command(name, argv, cwd)
        (checks_dir / ("%02d_%s.log" % (index, name))).write_text(result["output"], encoding="utf-8")
        results.append({k: v for k, v in result.items() if k != "output"})
    source_hashes = {}
    for pattern in ("*.py", "*.md", ".gitignore"):
        for path in sorted(ROOT.glob(pattern)):
            if path.is_file():
                source_hashes[path.name] = sha256(path)
    summary = {"results": results, "source_sha256": source_hashes}
    (checks_dir / "result.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if all(item["returncode"] == 0 for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
