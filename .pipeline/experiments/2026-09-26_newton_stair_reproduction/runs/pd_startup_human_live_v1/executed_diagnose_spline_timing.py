"""Native check of recorded curve timing, with explicitly labeled controls."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

from replay_local import BASE, BUILD, IMAGE, PROJECT


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    source = BASE / "runs/stair_native_walk_v2"
    all_curves = [json.loads(line)["data"] for line in (source / "artifacts/reactive_observations.jsonl").open()
                  if json.loads(line)["event"] == "bspline"]
    moving = [c for c in all_curves if any(p != c["pos_pts"][0] for p in c["pos_pts"])]
    if len(moving) != 2:
        raise ValueError("Expected two recorded moving curves")
    local_sources = [BUILD / "src/bspline_opt/src/uniform_bspline.cpp",
                     BUILD / "src/bspline_opt/include/bspline_opt/uniform_bspline.h",
                     BUILD / "src/plan_manage/config/planner.yaml"]
    expected = json.loads((BUILD / "source_sha256.json").read_text())
    for path in local_sources:
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected[str(path.relative_to(BUILD))]:
            raise ValueError("Native source changed")
    code = BASE / "scripts/diagnose_spline.cpp"
    shutil.copyfile(code, out / "executed_diagnose_spline.cpp")
    commands = [["g++", "-std=c++17", "-O2", "-I/usr/include/eigen3",
                 "-I" + str(BUILD / "src/bspline_opt/include"), str(local_sources[0]), str(code),
                 "-o", str(out / "native_spline_probe")]]
    cases = []
    for i, (curve, seed_duration) in enumerate(zip(moving, (0.853333333333, 1.6))):
        points, knots, degree = curve["pos_pts"], curve["knots"], curve["order"]
        duration = knots[-degree-1] - knots[degree]
        path = out / f"curve_{i}.txt"
        lines = [f"{len(points)} {degree} {len(knots)}"]
        lines += [" ".join(format(p[k], ".17g") for k in ("x", "y", "z")) for p in points]
        lines += [" ".join(format(k, ".17g") for k in knots)]
        path.write_text("\n".join(lines) + "\n")
        for condition, scale in (("recorded", 1.), ("same_geometry_seed_duration", seed_duration / duration)):
            output = out / f"curve_{i}_{condition}.json"
            cases.append({"curve": i, "condition": condition, "time_scale": scale, "output": output.name,
                          "seed_duration_from_log": seed_duration, "recorded_duration": duration})
            commands.append([str(out / "native_spline_probe"), str(path), format(scale, ".17g"), ">", str(output)])
    shell = ["set -e", " ".join(shlex.quote(x) for x in commands[0])]
    shell += [" ".join(shlex.quote(x) for x in command[:-2]) + " > " + shlex.quote(command[-1]) for command in commands[1:]]
    (out / "inside.sh").write_text("\n".join(shell) + "\n")
    name = "vla-native-spline-diagnosis"
    command = ["docker", "run", "--rm", "--pull=never", "--platform=linux/amd64", "--network=none",
        "--name", name, "--cpus=2", "--memory=3g", "-v", str(PROJECT) + ":" + str(PROJECT) + ":ro",
        "-v", str(out) + ":" + str(out) + ":rw", "--entrypoint", "/bin/bash", IMAGE, str(out / "inside.sh")]
    (out / "native_request.json").write_text(json.dumps({"command": command, "cases": cases,
        "source_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in local_sources},
        "limits": {"velocity": .75, "acceleration": .5, "feasibility_tolerance": .5},
        "claim": "Actual native feasibility check on published curves. Rescaled cases retain the final optimized geometry; they are not exact initializer-seed replays."}, indent=2) + "\n")
    try:
        with (out / "native.log").open("w") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=90)
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=15)
    report = []
    for case in cases:
        native = json.loads((out / case["output"]).read_text())
        report.append(case | {k:v for k,v in native.items() if not k.endswith("controls")})
    (out / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
