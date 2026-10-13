"""Run finite Docker probes and save compact evidence after every completed arm."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess


HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parents[1]
ROOT = EXPERIMENT.parents[2]
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-root", type=Path, required=True)
    parser.add_argument("--phase", choices=["comparisons", "lanes"], required=True)
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    if not args.attempt.isalnum():
        raise ValueError("Attempt must be alphanumeric")
    task = args.task_root.resolve(strict=True)
    assert (task / "prepared_inputs/identity.json").is_file()
    version = "v84" if args.phase == "comparisons" else "v85"
    compact = EXPERIMENT / "versions" / version / "results" / args.attempt
    compact.mkdir(parents=True, exist_ok=False)
    relative = EXPERIMENT.relative_to(ROOT)
    shell_prefix = ". /opt/ros/humble/setup.sh\n. /task/workspace/install/setup.sh\n"
    params = f"/repo/{relative}/versions/v81/sync_planner.yaml"

    def execute(name, executable, environment, output):
        command = ["docker", "run", "--rm", "--name", f"vla-{version}-{name}-{args.attempt}",
                   "--network", "none", "--cpus", "3", "--memory", "5g", "--platform", "linux/amd64",
                   "-v", f"{ROOT}:/repo:ro", "-v", f"{task}:/task",
                   "-e", "ROS_DOMAIN_ID=219", "-e", "ROS_LOCALHOST_ONLY=1"]
        for key, value in environment.items():
            command.extend(["-e", f"{key}={value}"])
        command.extend([IMAGE, "bash", "-c", shell_prefix +
                        f"exec {executable} --ros-args --params-file {params}\n"])
        log = task / "results" / f"{name}_{args.attempt}.log"
        with log.open("x") as stream:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
        shutil.copyfile(log, compact / log.name)
        if output.exists():
            destination = compact / name
            destination.mkdir()
            for path in output.iterdir():
                if path.suffix in (".json", ".jsonl"):
                    shutil.copyfile(path, destination / path.name)
        if result.returncode:
            raise RuntimeError(f"{name} failed: {result.returncode}; evidence retained")
        if (output / "summary.json").exists():
            print(json.dumps(json.loads((output / "summary.json").read_text())), flush=True)
        else:
            print(log.read_text().splitlines()[-1], flush=True)

    if args.phase == "comparisons":
        (task / "results/admission").mkdir(exist_ok=True)
        for schedule in ("nominal", "blackout"):
            for mode in ("fifo", "timer", "latest"):
                name = f"{schedule}_{mode}"
                execute(name, "/task/workspace/v84_probe/admission_probe", {
                    "V84_INPUT": "/task/prepared_inputs", "V84_OUTPUT": f"/task/results/admission/{name}",
                    "V84_MODE": mode, "V84_SCHEDULE": schedule,
                }, task / "results/admission" / name)
        execute("transient", "/task/workspace/v84_probe/transient_probe", {
            "V84_INPUT": "/task/prepared_inputs",
        }, task / "results/no_transient_directory")
    else:
        execute("lanes", "/task/workspace/v85_probe/lane_probe", {
            "V85_INPUT": "/task/prepared_inputs", "V85_OUTPUT": f"/task/results/lanes_{args.attempt}",
        }, task / "results" / f"lanes_{args.attempt}")


if __name__ == "__main__":
    main()
