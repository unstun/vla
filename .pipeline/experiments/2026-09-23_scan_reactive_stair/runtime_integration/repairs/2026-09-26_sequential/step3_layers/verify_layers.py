"""Actual native-header regressions and full selected-map monotonicity audit."""
import collections
import csv
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
P2B = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
SOURCE = P2B / "reactive_stair"
GROUND = HERE.parents[2] / "support_audit/ground.bin"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = HERE / "native_audit_v1"
    out.mkdir(exist_ok=False)
    expected_ground = "71550de5fde87043da3da73de00a8e1c1437c751bc939b87a718059d54949577"
    assert sha(GROUND) == expected_ground
    report = {"passed": False, "ground_sha256": expected_ground, "commands": [], "source_sha256": {},
              "compiler": subprocess.check_output(["c++", "--version"], text=True),
              "claim": "Native header C++ fixtures and real selected PCT geometry; no ROS or trajectory success claim."}

    def call(label, command, expected=0, stdout_path=None):
        value = subprocess.run(command, capture_output=True, text=True, timeout=40)
        (stdout_path or out / (label + ".log")).write_text(value.stdout)
        (out / (label + ".stderr.log")).write_text(value.stderr)
        report["commands"].append({"label": label, "command": command, "returncode": value.returncode})
        if value.returncode != expected:
            raise RuntimeError(label + " unexpected exit: " + value.stderr)

    tables = {}
    for build in ("scan_22", "scan_23"):
        header = P2B / "builds" / build / "src/plan_env/include"
        report["source_sha256"][build] = {p.name: sha(p) for p in (header / "plan_env").glob("*.h")}
        common = ["c++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-pedantic", "-I" + str(header)]
        flags = ["-DSAME_LEVEL_BOUND_FIXED"] if build == "scan_23" else []
        executable = out / (build + "_regression")
        call(build + "_compile_regression", common + flags + [str(SOURCE / "test_same_level_support.cpp"), "-o", str(executable)])
        call(build + "_regression", [str(executable)], expected=0 if build == "scan_23" else 1)
        if build == "scan_23":
            existing = out / "scan_23_existing_regressions"
            call("existing_compile", common + [str(SOURCE / "test_eth_step_score_adaptation.cpp"), "-o", str(existing)])
            call("existing_regressions", [str(existing)])
        executable = out / (build + "_audit")
        call(build + "_compile_audit", common + [str(SOURCE / "audit_terrain_layers.cpp"), "-o", str(executable)])
        table = out / (build + "_support.csv")
        call(build + "_audit", [str(executable), str(GROUND)], stdout_path=table)
        with table.open() as stream:
            tables[build] = {(r["ix"], r["iy"], r["layer"]): r for r in csv.DictReader(stream)}
    old, new = tables["scan_22"], tables["scan_23"]
    assert old.keys() == new.keys()
    old_free = {k for k, v in old.items() if v["support"] in ("1", "2")}
    new_free = {k for k, v in new.items() if v["support"] in ("1", "2")}
    report["new_free_subset_of_old"] = new_free <= old_free
    assert report["new_free_subset_of_old"]
    report["counts"] = {b: dict(collections.Counter(v["support"] for v in rows.values())) for b, rows in tables.items()}
    report["support_legend"] = {"0": "Unknown", "1": "Flat", "2": "Stair", "3": "Unsupported"}
    report["unchanged_traversable_records"] = len(new_free)
    report["newly_blocked_records"] = len(old_free - new_free)
    report["label_transitions"] = dict(collections.Counter(old[k]["support"] + "->" + new[k]["support"] for k in old))
    # Prior logged diagnostic cylinder point; show nearby lower/upper layers.
    report["diagnostic_region"] = [{"before": old[k], "after": new[k]} for k in old
        if abs(float(old[k]["x"]) + 5.59778) < .06 and abs(float(old[k]["y"]) - 5.82081) < .06]
    report["passed"] = True
    report["files_sha256"] = {p.name: sha(p) for p in out.iterdir() if p.is_file()}
    (out / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("passed", "counts", "newly_blocked_records", "label_transitions", "diagnostic_region")}, indent=2))


if __name__ == "__main__":
    main()
