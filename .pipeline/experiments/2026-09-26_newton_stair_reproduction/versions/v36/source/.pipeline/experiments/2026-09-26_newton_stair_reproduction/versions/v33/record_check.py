"""Review round 1, B1: the trial's pre-physics source-record check, run read-only on v33's bytes.

scripts/run_local_episode.py re-hashes every record of setup/runtime_sources.json before physics and raises
"Archived runtime source changed" on a mismatch. scripts/review_local_episode.py records the same comparison, for
setup/source_identity.json and setup/runtime_sources.json, as its source_identity check. This script:
- executes run_local_episode.py's three lines verbatim, read from the script by their text;
- recomputes the review's comparison, after checking that its lines are present verbatim;
- as a negative control, compares v32's record (parent_source/setup/runtime_sources.json) with the current files,
  which must find exactly the three changed runtime files: the round-1 state that would have been refused.
Writes record_check.json next to this script and exits non-zero on failure.
"""
import hashlib
import json
from pathlib import Path
import sys
import textwrap

H = Path(__file__).resolve().parent
E = H.parents[1]
LAUNCH = ('    for record in json.loads((BASE / "setup/runtime_sources.json").read_text())["records"]:\n'
          '        if hashlib.sha256((BASE / record["path"]).read_bytes()).hexdigest() != record["sha256"]:\n'
          '            raise ValueError("Archived runtime source changed")\n')
REVIEW = ('    for manifest, key in (("source_identity.json", "inputs"), ("runtime_sources.json", "records")):\n'
          '        records = read(BASE / "setup" / manifest)[key]\n'
          '        source_checks[manifest] = {"files": len(records), "mismatches": [r["path"] for r in records\n'
          '            if sha(BASE / r["path"]) != r["sha256"]]}\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    launch_text = (E / "scripts/run_local_episode.py").read_text()
    review_text = (E / "scripts/review_local_episode.py").read_text()
    report = {"launch_lines_found": launch_text.count(LAUNCH) == 1, "review_lines_found": review_text.count(REVIEW) == 1}
    try:
        exec(textwrap.dedent(LAUNCH), {"BASE": E, "json": json, "hashlib": hashlib})
        report["launch_check"] = "passed"
    except ValueError as exc:
        report["launch_check"] = str(exc)
    source_checks = {}
    exec(textwrap.dedent(REVIEW), {"BASE": E, "read": lambda p: json.loads(Path(p).read_text()), "sha": sha,
                                   "source_checks": source_checks})
    report["review_source_checks"] = source_checks
    parent = json.loads((H / "parent_source/setup/runtime_sources.json").read_text())["records"]
    report["negative_control_v32_record_mismatches"] = [r["path"] for r in parent if sha(E / r["path"]) != r["sha256"]]
    report["passed"] = (report["launch_lines_found"] and report["review_lines_found"] and report["launch_check"] == "passed"
                        and all(not c["mismatches"] for c in source_checks.values())
                        and report["negative_control_v32_record_mismatches"] == [
                            "runtime_sources/backend_adapter/backend_adapter/contracts.py",
                            "runtime_sources/backend_adapter/backend_adapter/control_gate.py",
                            "runtime_sources/backend_ros/p2b_backend_ros/node.py"])
    (H / "record_check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
