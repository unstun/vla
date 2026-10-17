"""Pair exact captured native curves with the same measured native-map input."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

from materialize import BASE, HERE


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    build = BASE / "runtime/scan42_geometry_v7"
    source = BASE / "replays/flat_curve_capture_native42_v7/result/captured_curves.json"
    curves = json.loads(source.read_text())[:2]
    shutil.copyfile(source, out / "captured_curves.json")
    cpp = HERE / "sample_native_curve.cpp"
    shutil.copyfile(cpp, out / "executed_sample_native_curve.cpp")
    binary = out / "native_sampler"
    compile_command = ["g++", "-std=c++17", "-O2", "-I/usr/include/eigen3",
                       "-I"+str(build/"src/bspline_opt/include"), "-I"+str(build/"src/plan_env/include"),
                       str(build/"src/bspline_opt/src/uniform_bspline.cpp"), str(out/"executed_sample_native_curve.cpp"), "-o", str(binary)]
    shell = ["set -e", shlex.join(compile_command)]
    for curve in curves:
        case = out / curve["stage"]
        shutil.copytree(BASE / "runs/generic_temporal_sensor_v1/static_human_detour", case)
        rows = [f'{len(curve["controls"])} 3 {len(curve["knots"])}']
        rows += [" ".join(format(x,".17g") for x in p) for p in curve["controls"]]
        rows += [" ".join(format(x,".17g") for x in curve["knots"])]
        (case / "curve.txt").write_text("\n".join(rows)+"\n")
        shell.append(shlex.join([str(binary),str(case/"curve.txt"),str(case/"queries.txt")])+
                     " > "+shlex.quote(str(case/"sampling.json")))
    (out / "inside.sh").write_text("\n".join(shell)+"\n")
    command = ["docker","run","--rm","--pull=never","--platform=linux/amd64","--network=none",
               "--memory=2g","--cpus=2","-v",str(BASE)+":"+str(BASE)+":ro",
               "-v",str(out)+":"+str(out)+":rw","--entrypoint","/bin/bash",
               "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb",str(out/"inside.sh")]
    with (out/"native.log").open("w") as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=80)
    cases=[]
    for curve in curves:
        case=out/curve["stage"]
        cases.append({"case":curve["stage"],"sha256":{p.name:sha(p) for p in case.iterdir() if p.is_file()}})
    (out/"result.json").write_text(json.dumps({"cases":cases,"command":command,
        "captured_curves_sha256":sha(source),"native_sampler_sha256":sha(cpp),
        "claim":"Exact native complete-curve samples and same raw clouds. exact_z/body_yaw are diagnostic query controls only, never navigation inputs."},indent=2)+"\n")


if __name__ == "__main__":
    main()
