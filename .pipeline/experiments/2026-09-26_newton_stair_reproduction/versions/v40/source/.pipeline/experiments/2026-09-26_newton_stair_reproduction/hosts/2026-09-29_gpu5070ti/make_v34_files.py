"""Derive v34's trial runner and pre-physics gate check from v33's reviewed files, by substitution only.

- v34_trial_run.sh from v33_trial_run.sh (sha256 2649f0e8..., confirmed by the port's fifth review round): every
  "v33" becomes "v34" (the run IDs, the host-file directory, the lock, the refusal file, the plan and host-note
  references, the integration version and the planner copy), and runtime/scan64_input_refresh_v31 becomes
  runtime/scan65_evidence_floor_v34. Nothing else changes; the script asserts that the text is the substitutions'
  line-by-line image, that every changed line held one of the substituted strings, and that no "v33" or "scan64"
  remains. The changed line numbers are recorded for review.
- checks/p1_gates_v34.py from checks/p1_gates.py by the same substitutions (the scratch directory also gets its own
  name), plus one gate the launcher applies to geometry-only episodes (scripts/run_local_episode.py lines 158-162):
  the native build's source manifest must equal a reviewed candidate identity in repairs/2026-09-26_generic_occupancy.
Writes both files and make_v34_files.json (their SHA-256s and the substitution check).
Usage: python3 make_v34_files.py
"""
from pathlib import Path
import hashlib, json

H = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
SUBSTITUTIONS = [("runtime/scan64_input_refresh_v31", "runtime/scan65_evidence_floor_v34"), ("v33", "v34")]


def derive(source, target, extra=()):
    text = source.read_text()
    new = text
    for old, rep in list(SUBSTITUTIONS) + list(extra):
        new = new.replace(old, rep)
    assert "v33" not in new and "scan64" not in new, target
    old_lines, new_lines = text.splitlines(), new.splitlines()
    assert len(old_lines) == len(new_lines)
    changed = []
    for i, (a, b) in enumerate(zip(old_lines, new_lines)):
        if a == b:
            continue
        forward = a
        for old, rep in list(SUBSTITUTIONS) + list(extra):
            forward = forward.replace(old, rep)
        assert forward == b and ("v33" in a or "scan64" in a or any(o in a for o, _ in extra)), (i + 1, a, b)
        changed.append(i + 1)
    target.write_text(new)
    return {"source": source.name, "source_sha256": sha(source), "target": str(target.relative_to(H)),
            "target_sha256": sha(target), "lines": len(new_lines), "changed_lines": changed}


record = {"runner": derive(H / "v33_trial_run.sh", H / "v34_trial_run.sh")}
assert record["runner"]["source_sha256"].startswith("2649f0e8"), record["runner"]["source_sha256"]
gates = derive(H / "checks/p1_gates.py", H / "checks/p1_gates_v34.py", extra=[("p1_scratch", "p1_scratch_v34")])
text = (H / "checks/p1_gates_v34.py").read_text()
anchor = 'import shutil\nout["free_disk"]'
addition = '''# reviewed candidate (run_local_episode.py lines 158-162, applied to geometry-only episodes such as the trial)
identities = [json.loads(p.read_text()) for p in (BASE / "repairs/2026-09-26_generic_occupancy").glob("candidate*identity*.json")]
out["reviewed_candidate"] = {"passed": any(json.loads((N / "source_sha256.json").read_text()) == i["source_sha256"] for i in identities),
                             "identities_checked": len(identities)}
'''
assert text.count(anchor) == 1
(H / "checks/p1_gates_v34.py").write_text(text.replace(anchor, addition + anchor))
gates["target_sha256"] = sha(H / "checks/p1_gates_v34.py")
gates["added"] = "reviewed_candidate gate (launcher lines 158-162)"
record["gates"] = gates
(H / "make_v34_files.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
