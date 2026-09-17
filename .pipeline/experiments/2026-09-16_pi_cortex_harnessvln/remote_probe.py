"""Sync a bounded offline probe to the selected host and return all evidence."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parent
HOST = "gpu5070ti"
REMOTE = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln"
NODE = "/home/sun/vla_exec/2026-09-16_mip_5070ti/tools/node-v24.21.0-linux-x64/bin"


def main():
    output = ROOT / "remote_results" / datetime.now(timezone.utc).strftime("probe_%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True)
    paths = ["gateway.py", "serve_fixture.py", "test_gateway.py", "verify.py",
             "pi/package.json", "pi/package-lock.json"]
    paths += [str(path.relative_to(ROOT)) for path in sorted((ROOT / "pi").glob("*.mjs"))]
    paths += [str(path.relative_to(ROOT)) for path in sorted((ROOT / "pi" / "test").glob("*.mjs"))]
    expected = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
    (output / "source_sha256.json").write_text(json.dumps(expected, indent=2) + "\n")
    (output / "files.txt").write_text("\n".join(paths) + "\n")
    records = []

    def run(command, label, stdin=None, timeout=180):
        result = subprocess.run(command, input=stdin, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=timeout)
        (output / f"{label}.log").write_text(result.stdout)
        records.append({"label": label, "command": command, "exit_code": result.returncode})
        print(f"{label}: exit {result.returncode}", flush=True)
        if result.returncode:
            raise RuntimeError(f"{label} failed: {result.stdout[-2000:]}")
        return result.stdout

    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", HOST]
    try:
        run(ssh + [shlex.join(["mkdir", "-p", REMOTE])], "mkdir")
        run(["rsync", "-a", "--files-from=" + str(output / "files.txt"),
             str(ROOT) + "/", f"{HOST}:{REMOTE}/"], "sync_source")
        verify = (
            "import hashlib,json,pathlib,sys\n"
            f"root=pathlib.Path({REMOTE!r})\n"
            f"expected={expected!r}\n"
            "actual={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in expected}\n"
            "print(json.dumps({'all_match':actual==expected,'source':actual},indent=2))\n"
            "sys.exit(0 if actual==expected else 1)\n"
        )
        run(ssh + ["python3 -"], "source_gate", stdin=verify)
        environment = ["env", f"PATH={NODE}:/usr/local/bin:/usr/bin:/bin"]
        install = environment + ["npm", "--prefix", REMOTE + "/pi", "ci", "--ignore-scripts", "--no-audit", "--no-fund"]
        run(ssh + [shlex.join(install)], "npm_ci")
        run(ssh + [shlex.join(environment + ["python3", REMOTE + "/verify.py"])], "verify", timeout=180)
        for folder in ["checks", "runs"]:
            run(["rsync", "-a", f"{HOST}:{REMOTE}/{folder}/", str(output / folder) + "/"], f"return_{folder}")
        remote_hash = (
            "import hashlib,json,pathlib\n"
            f"root=pathlib.Path({REMOTE!r})\n"
            "files=sorted(p for d in ['checks','runs'] for p in (root/d).rglob('*') if p.is_file())\n"
            "print(json.dumps({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2))\n"
        )
        raw = run(ssh + ["python3 -"], "artifact_hashes", stdin=remote_hash)
        hashes = json.loads(raw)
        if not hashes or any(hashlib.sha256((output / name).read_bytes()).hexdigest() != digest
                             for name, digest in hashes.items()):
            raise RuntimeError("Returned artifact hash mismatch")
        report = {"all_passed": True, "source_gate_passed": True,
                  "returned_artifacts_match": True, "returned_file_count": len(hashes),
                  "host": HOST, "remote_root": REMOTE,
                  "evidence_kind": "offline_protocol_probe_on_linux",
                  "actual_llm_calls": 0, "cortex_runtime_executed": False,
                  "habitat_executed": False, "commands": records}
        (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(output, flush=True)
    except Exception as error:
        (output / "result.json").write_text(json.dumps({"all_passed": False, "error": str(error),
                                                       "commands": records}, indent=2) + "\n")
        raise


if __name__ == "__main__":
    main()
