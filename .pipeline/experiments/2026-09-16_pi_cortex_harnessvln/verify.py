"""Record bounded local checks and a scripted run using the actual Pi package."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    run_id = datetime.now(timezone.utc).strftime("checks_%Y%m%dT%H%M%SZ")
    output = ROOT / "checks" / run_id
    output.mkdir(parents=True)
    commands = [
        (ROOT, [sys.executable, "-m", "unittest", "-v", "test_gateway.py"]),
        (ROOT / "pi", ["npm", "test"]),
        (ROOT / "pi", ["npm", "run", "smoke"]),
    ]
    commands.extend((ROOT, ["node", "--check", str(file)]) for file in sorted((ROOT / "pi").glob("*.mjs")))
    records = []
    for index, (cwd, command) in enumerate(commands):
        result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, timeout=60)
        log = output / f"{index:02d}.log"
        log.write_text(result.stdout)
        records.append({"command": command, "cwd": str(cwd.relative_to(ROOT)),
                        "exit_code": result.returncode, "log": log.name})
        print(f"{command[0]} {' '.join(command[1:])}: exit {result.returncode}", flush=True)
        if result.returncode:
            print(result.stdout)
            break
    files = list(ROOT.glob("*.py")) + list((ROOT / "pi").glob("*.mjs"))
    files += list((ROOT / "pi" / "test").glob("*.mjs"))
    files += [ROOT / "pi" / "package.json", ROOT / "pi" / "package-lock.json"]
    source = {str(file.relative_to(ROOT)): hashlib.sha256(file.read_bytes()).hexdigest()
              for file in sorted(files)}
    (output / "source_sha256.json").write_text(json.dumps(source, indent=2) + "\n")
    report = {"evidence_kind": "offline_protocol_checks", "checks": records,
              "all_passed": len(records) == len(commands) and all(item["exit_code"] == 0 for item in records),
              "python": sys.version, "node": subprocess.check_output(["node", "--version"], text=True).strip(),
              "cortex_runtime_executed": False, "habitat_executed": False, "actual_llm_calls": 0}
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(output)
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
