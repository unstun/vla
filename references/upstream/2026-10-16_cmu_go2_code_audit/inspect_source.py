"""Record source provenance and cross-component configuration facts; run no robot code."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
REPO = ROOT / "source/autonomy_stack_go2"
PIN = "43d5f54b389b251713f0097893c30fa76c870d54"


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args], text=True).strip()


def params(relative):
    tree = ET.parse(REPO / relative)
    return {n.attrib["name"]: n.attrib.get("value") for n in tree.findall(".//param")}


def ply_summary(relative):
    lines = (REPO / relative).read_text().splitlines()
    start = lines.index("end_header") + 1
    rows = [line.split() for line in lines[start:] if line.strip()]
    return {"rows": len(rows), "minimum_z": min(float(r[2]) for r in rows),
            "maximum_z": max(float(r[2]) for r in rows),
            "groups": len({r[-1] for r in rows})}


if __name__ == "__main__":
    assert git("rev-parse", "HEAD") == PIN
    assert not git("status", "--porcelain")
    tree = git("ls-tree", "-r", "HEAD")
    inventory = {}
    for line in tree.splitlines():
        path = line.split("\t", 1)[1]
        file = REPO / path
        if file.is_file() and not file.is_symlink():
            inventory[path] = hashlib.sha256(file.read_bytes()).hexdigest()
    (ROOT / "source_inventory.json").write_text(json.dumps({
        "commit": PIN, "upstream_worktree_clean": True,
        "git_tree_sha256": hashlib.sha256(tree.encode()).hexdigest(),
        "tree_paths": len(tree.splitlines()), "materialized_files": len(inventory),
        "file_sha256": inventory,
    }, indent=2) + "\n")

    packages = []
    for path in sorted(REPO.rglob("package.xml")):
        package = ET.parse(path).getroot()
        packages.append({"name": package.findtext("name"),
                         "path": str(path.relative_to(REPO)),
                         "declared_licenses": [n.text for n in package.findall("license")],
                         "dependencies": sorted({n.text for n in package
                                                  if "depend" in n.tag and n.text})})
    (ROOT / "package_inventory.json").write_text(json.dumps(packages, indent=2) + "\n")

    local = params("src/base_autonomy/local_planner/launch/local_planner.launch")
    terrain = params("src/base_autonomy/terrain_analysis/launch/terrain_analysis.launch")
    far = (REPO / "src/route_planner/far_planner/config/default.yaml").read_text()
    free_z = float(re.search(r"util/terrain_free_Z:\s*([0-9.]+)", far)[1])
    obstacle = float(local["obstacleHeightThre"])
    use_cost = local["useCost"] == "true"
    examples = []
    for height in (0.10, 0.18, 0.30, 0.35):
        examples.append({"terrain_intensity_m": height,
                         "retained_by_local_terrain_filter": height > obstacle or use_cost,
                         "far_classification": "free" if height < free_z else "obstacle"})
    result = {
        "commit": PIN, "status": "static_source_and_configuration_inspection",
        "local_parameters": local, "terrain_parameters": terrain,
        "far_free_height_threshold_m": free_z,
        "far_multi_layer_enabled": bool(re.search(r"is_multi_layer:\s*true", far)),
        "height_examples": examples,
        "height_example_boundary": "Illustration of source predicates for the same retained terrain value; not sensor simulation, stair-height certification, or full-route failure proof.",
        "path_tables": {name: ply_summary("src/base_autonomy/local_planner/paths/" + name)
                        for name in ("startPaths.ply", "pathList.ply")},
        "packages": len(packages),
        "upstream_build_executed": False, "upstream_navigation_executed": False,
        "physics_executed": False,
    }
    (ROOT / "source_facts.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"materialized_files": len(inventory), "packages": len(packages),
                      "height_examples": examples, "path_tables": result["path_tables"]}, indent=2))
