"""K1 and K2 of versions/v33/PLAN.md.

K1 byte-exact: re-applying materialize.py's edits to the preimages in parent_source/ gives the current files,
undoing them gives the preimages back, the preimages match prepared.json's parent hashes, and every other
v32 manifest file is unchanged.
K2 scope: each changed file compiles, and an AST comparison with its preimage finds changes only in the
definitions PLAN.md lists (module statements outside them identical).
Writes check_change.json next to this script and exits non-zero on failure.
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

H = Path(__file__).resolve().parent
E = H.parents[1]
R = E.parents[2]
ALLOWED = {
    # The two dataclasses, fields and validation (__post_init__) included.
    "runtime_sources/backend_adapter/backend_adapter/contracts.py": {
        "MeasuredState", "MeasuredState.__post_init__", "GateConfig", "GateConfig.__post_init__"},
    "runtime_sources/backend_adapter/backend_adapter/control_gate.py": {
        "CommandGate.__init__", "CommandGate._blocking_reason", "CommandGate.measurement_stale"},
    "runtime_sources/backend_ros/p2b_backend_ros/node.py": {
        "RosScanPort.__init__", "RosScanPort.measurement_provider", "RosScanPort.snapshot", "RosScanPort._on_body_pose",
        "RosScanPort.sim_now", "RosScanPort._on_sim_clock"},
    "scripts/native_graph.py": {"main"},
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def definitions(source):
    """Qualified name -> dump for top-level functions, classes (whole) and methods; plus the other module statements."""
    tree = ast.parse(source)
    defs, rest = {}, []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs[node.name] = ast.dump(node)
        elif isinstance(node, ast.ClassDef):
            members = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    defs[f"{node.name}.{item.name}"] = ast.dump(item)
                else:
                    members.append(ast.dump(item))
            defs[node.name + ".<class body>"] = json.dumps(members) + ast.dump(ast.ClassDef(
                name=node.name, bases=node.bases, keywords=node.keywords, body=[], decorator_list=node.decorator_list))
        else:
            rest.append(ast.dump(node))
    return defs, rest


def main():
    spec = importlib.util.spec_from_file_location("materialize", H / "materialize.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    prepared = json.loads((H / "prepared.json").read_text())
    parent = json.loads((H.parent / "v32/manifest.json").read_text())
    report, ok = {"files": {}}, True
    for name in prepared["changed_files"]:
        path = R / name
        relative = str(path.relative_to(E))
        before = (H / "parent_source" / relative).read_bytes()
        current = path.read_bytes()
        rebuilt = before
        for p, anchor, text, where in module.EDITS:
            if p == path:
                assert rebuilt.count(anchor) == 1
                rebuilt = module.apply(rebuilt, anchor, text, where)
        undone = current
        for p, anchor, text, where in reversed(module.EDITS):
            if p == path:
                new = {"after": anchor + text, "before": text + anchor, "replace": text}[where]
                undone = undone.replace(new, anchor) if undone.count(new) == 1 else b"<not unique>"
        compile(current, name, "exec")
        old_defs, old_rest = definitions(before)
        new_defs, new_rest = definitions(current)
        changed = {k for k in set(old_defs) | set(new_defs) if old_defs.get(k) != new_defs.get(k)}
        # A changed method also changes nothing else; a changed dataclass shows as "<class body>".
        changed_names = {k.replace(".<class body>", "") for k in changed}
        entry = {"k1_rebuilt_equals_current": rebuilt == current,
                 "k1_undone_equals_preimage": undone == before,
                 "k1_preimage_matches_parent_hash": sha(before) == prepared["before_sha256"][name],
                 "k1_current_matches_prepared_hash": sha(current) == prepared["after_sha256"][name],
                 "k2_compiles": True,
                 "k2_changed_definitions": sorted(changed_names),
                 "k2_other_module_statements_identical": old_rest == new_rest,
                 "k2_within_allowed": changed_names <= ALLOWED[relative],
                 "added_lines": current.count(b"\n") - before.count(b"\n")}
        entry["passed"] = all(v for k, v in entry.items() if k.startswith(("k1_", "k2_")) and isinstance(v, bool))
        report["files"][relative] = entry
        ok = ok and entry["passed"]
    others = {n: d for n, d in parent["source_files"].items() if n not in prepared["changed_files"]}
    mismatched = [n for n, d in others.items() if sha((R / n).read_bytes()) != d]
    report["k1_other_v32_files_unchanged"] = not mismatched
    report["k1_other_v32_files_checked"] = len(others)
    report["k1_mismatched"] = mismatched
    report["passed"] = ok and not mismatched
    (H / "check_change.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: (v["passed"], v["k2_changed_definitions"]) for k, v in report["files"].items()}, indent=1))
    print("passed", report["passed"], "other files", len(others), "mismatched", mismatched)
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
