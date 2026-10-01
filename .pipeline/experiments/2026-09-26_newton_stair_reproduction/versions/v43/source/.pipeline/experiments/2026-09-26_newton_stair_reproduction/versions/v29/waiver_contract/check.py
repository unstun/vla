"""Judge the red/green waiver contract (versions/v29/PLAN.md step 2); writes contract_results.json."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
STATES = ("stopped", "z_0p3650", "control")
load = lambda path: json.loads(path.read_text())
red = {state: load(HERE / "red_v28" / f"{state}.json") for state in STATES}
green = {state: load(HERE / "green_v29" / f"{state}.json") for state in STATES}
checks = {}
for state in STATES:
    r, g = red[state], green[state]
    informative = lambda result, name: result["categories"].get(name, {}).get("informative", 0)
    checks[state] = {
        "exit_codes_zero": all((HERE / label / f"{state}_exit_code.txt").read_text().strip() == "0" for label in ("red_v28", "green_v29")),
        "pose_fresh_and_waiver_enabled": all(x["pose_fresh"] and x["waiver_enabled"] for x in (r, g)),
        "no_sub_voxel_errors": r["sub_voxel_errors"] == g["sub_voxel_errors"] == 0,
        "same_points": r["points"] == g["points"] and r["categories"] == g["categories"],
        "red_matches_v28_oracle": r["mismatches_vs_v28_spec"] == 0,
        "red_differs_from_v29_oracle": r["mismatches_vs_v29_spec"] > 0,
        "green_matches_v29_oracle": g["mismatches_vs_v29_spec"] == 0,
        "green_differs_from_v28_oracle": g["mismatches_vs_v28_spec"] > 0,
        "stale_pose_never_free": r["stale_pose"]["free_while_stale"] == g["stale_pose"]["free_while_stale"] == 0
                                 and g["stale_pose"]["checked"] > 0,
        "non_unknown_results_identical": r["digest_not_unknown"] == g["digest_not_unknown"],
        "agreeing_unknown_results_identical": r["digest_unknown_where_specs_agree"] == g["digest_unknown_where_specs_agree"],
        "v29_only_informative_points": informative(g, "v29_only"),
        "v28_only_informative_points": informative(g, "v28_only"),
        "red_mismatches_vs_v29": r["mismatches_vs_v29_spec"], "green_mismatches_vs_v28": g["mismatches_vs_v28_spec"],
        "categories": g["categories"], "stale_checked": g["stale_pose"]["checked"],
    }
passed = all(all(v for k, v in item.items() if isinstance(v, bool)) and item["v29_only_informative_points"] > 0
             for item in checks.values())
(HERE / "contract_results.json").write_text(json.dumps({"passed": passed, "states": checks}, indent=2) + "\n")
print(json.dumps({"passed": passed, **{s: {k: v for k, v in c.items() if k != "categories"} for s, c in checks.items()}}, indent=1))
