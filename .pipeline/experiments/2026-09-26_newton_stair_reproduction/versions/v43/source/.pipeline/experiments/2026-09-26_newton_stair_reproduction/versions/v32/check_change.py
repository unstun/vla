"""K1 and K2 for v32: byte-exact insertions and an AST that differs from v31 only by them.

K1: the preimage in parent_source/ has v31's pinned SHA-256; removing the three insertions from the
current scripts/newton_episode.py restores those bytes; every other v31 source file is unchanged.
K2: the current file compiles; deleting from its AST exactly `import gc`, the `gc.collect()` and
`gc.freeze()` statements immediately before the control loop, and the
`if (step + 1) % 50 == 0: gc.collect(); gc.freeze()` statement immediately after
`last_snapshot = snapshot` gives an AST identical to v31's (ast.dump, without line attributes).
Writes check_change.json.
"""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
EPISODE = BASE / "scripts/newton_episode.py"
sha = lambda data: hashlib.sha256(data).hexdigest()


def is_call(node, name):
    return (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and not node.value.args
            and not node.value.keywords and ast.unparse(node.value.func) == name)


def strip(tree):
    removed = []
    imports = [n for n in tree.body if isinstance(n, ast.Import) and [a.name for a in n.names] == ["gc"]]
    assert len(imports) == 1
    tree.body.remove(imports[0])
    removed.append("import gc")
    for parent in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(parent, field, None)
            if not isinstance(block, list):
                continue
            for index in range(len(block) - 1, -1, -1):
                if index >= len(block):
                    continue
                node = block[index]
                if is_call(node, "gc.freeze") and index >= 1 and is_call(block[index - 1], "gc.collect") \
                        and index + 1 < len(block) and isinstance(block[index + 1], ast.For) \
                        and ast.unparse(block[index + 1].target) == "step":
                    del block[index - 1:index + 1]
                    removed.append("collect and freeze before the control loop")
                elif isinstance(node, ast.If) and ast.unparse(node.test) == "(step + 1) % 50 == 0" \
                        and len(node.body) == 2 and is_call(node.body[0], "gc.collect") \
                        and is_call(node.body[1], "gc.freeze") and not node.orelse and index > 0 \
                        and ast.unparse(block[index - 1]) == "last_snapshot = snapshot":
                    del block[index]
                    removed.append("collect and freeze every 50 steps")
    return removed


def main():
    parent = json.loads((HERE.parent / "v31/manifest.json").read_text())
    prepared = json.loads((HERE / "prepared.json").read_text())
    name = str(EPISODE.relative_to(ROOT))
    before = (HERE / "parent_source" / EPISODE.relative_to(BASE)).read_bytes()
    after = EPISODE.read_bytes()
    unchanged = all(sha((ROOT / n).read_bytes()) == d for n, d in parent["source_files"].items() if n != name)
    import importlib.util
    spec = importlib.util.spec_from_file_location("v32_materialize", HERE / "materialize.py")
    materialize = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(materialize)
    restored = after
    for anchor, inserted, where in materialize.INSERTIONS:
        block = inserted + anchor if where == "before" else anchor + inserted
        assert restored.count(block) == 1
        restored = restored.replace(block, anchor)
    tree_after, tree_before = ast.parse(after), ast.parse(before)
    compile(after, str(EPISODE), "exec")
    removed = strip(tree_after)
    same_ast = ast.dump(tree_after) == ast.dump(tree_before)
    result = {
        "K1": {"preimage_is_v31": sha(before) == parent["source_files"][name],
               "removing_insertions_restores_v31": restored == before,
               "after_matches_prepared": sha(after) == prepared["episode_after_sha256"],
               "added_lines": after.count(b"\n") - before.count(b"\n"),
               "only_insertions": all(line in after.decode().splitlines() for line in before.decode().splitlines()),
               "other_v31_sources_unchanged": unchanged},
        "K2": {"compiles": True, "removed_nodes": removed, "ast_equal_after_removal": same_ast},
    }
    result["passed"] = (all(result["K1"][k] for k in ("preimage_is_v31", "removing_insertions_restores_v31",
                                                      "after_matches_prepared", "only_insertions",
                                                      "other_v31_sources_unchanged"))
                        and sorted(removed) == sorted(["import gc", "collect and freeze before the control loop",
                                                       "collect and freeze every 50 steps"]) and same_ast)
    (HERE / "check_change.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
