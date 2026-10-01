"""Show which synthetic case catches each wrong variant of the v30 rule: python3 mutation_check.py.

Each variant changes oracle.py in one way. The script scores every case in
cases.txt and lists the cases whose edge-cell label then misses the plan
table (check.py EXPECTED, v30 column). Writes mutation_results.json.
"""
from pathlib import Path
import json, math, sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import oracle  # noqa: E402

# check.py's case parser and evidence builder, without running its checks.
namespace = {"__file__": str(HERE / "check.py")}
exec((HERE / "check.py").read_text().split("cases = parse_cases()")[0], namespace)
cases, evidence_for = namespace["parse_cases"](), namespace["evidence_for"]
EXPECTED, TARGET = namespace["EXPECTED"], namespace["TARGET"]
SOURCE = (HERE / "oracle.py").read_text()


def lattice(mapping):
    def height(evidence, nav, cell, elevation):
        if evidence is None:
            return None
        x, y = mapping(nav, cell)
        surfaces = evidence.cells.get((math.floor((x - evidence.origin[0]) / evidence.resolution),
                                       math.floor((y - evidence.origin[1]) / evidence.resolution)))
        k = -1 if surfaces is None else oracle.nearest(surfaces, elevation)
        return None if k < 0 else surfaces[k]
    return height


EDITS = {
    "evidence_used_for_absent_neighbours": ("""                if surfaces is None:
                    continue
                k = nearest(surfaces, elevation)
                height = surfaces[k] if k >= 0 else evidence_height(evidence, nav, neighbour, elevation)""",
                                            """                if surfaces is None:
                    h = evidence_height(evidence, nav, neighbour, elevation)
                    if h is not None:
                        low, high = min(low, h), max(high, h)
                    continue
                k = nearest(surfaces, elevation)
                height = surfaces[k] if k >= 0 else evidence_height(evidence, nav, neighbour, elevation)"""),
    "ambiguity_ignored": ("""        elif abs(distance - best) <= 1e-9:
            ambiguous = True""", """        elif abs(distance - best) <= 1e-9:
            pass"""),
    "skip_instead_of_evidence_height": ("height = surfaces[k] if k >= 0 else evidence_height(evidence, nav, neighbour, elevation)\n                if height is None:",
                                        "height = surfaces[k] if k >= 0 else evidence_height(evidence, nav, neighbour, elevation)\n                if k < 0 and height is not None:\n                    continue\n                if height is None:"),
}


def score_all(module):
    out = {}
    for name, case in cases.items():
        evidence = evidence_for(case)
        if evidence is not None:
            evidence = module.Snapshot(evidence.cells, evidence.origin, evidence.resolution, evidence.frame)
        out[name] = module.score(module.Snapshot(case["nav"]), evidence)[TARGET][0][0]
    return out


def failing(labels):
    return [name for name in cases if labels[name] != EXPECTED[name][1]]


results = {"faithful_rule": failing(score_all(oracle))}
original = oracle.evidence_height
LOOKUPS = {
    # The evidence cell with the navigation cell's own index, ignoring both origins.
    "identity_lattice": lambda evidence, nav, cell, elevation: (
        None if evidence is None or cell not in evidence.cells or oracle.nearest(evidence.cells[cell], elevation) < 0
        else evidence.cells[cell][oracle.nearest(evidence.cells[cell], elevation)]),
    # The evidence cell under the navigation cell's corner instead of its centre.
    "corner_lattice": lattice(lambda nav, c: (nav.origin[0] + c[0] * nav.resolution, nav.origin[1] + c[1] * nav.resolution)),
}
for name, lookup in LOOKUPS.items():
    oracle.evidence_height = lookup
    results[name] = failing(score_all(oracle))
oracle.evidence_height = original
for name, (old, new) in EDITS.items():
    assert SOURCE.count(old) == 1, name
    module = type(sys)("mutant_" + name)
    exec(compile(SOURCE.replace(old, new), "mutant_" + name, "exec"), module.__dict__)
    results[name] = failing(score_all(module))
passed = results["faithful_rule"] == [] and all(results[k] for k in results if k != "faithful_rule")
(HERE / "mutation_results.json").write_text(json.dumps({"passed": passed, "cases_that_catch_each_variant": results}, indent=2) + "\n")
print(json.dumps({"passed": passed, **results}, indent=1))
