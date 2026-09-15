"""Run the predeclared two-language comparison sequentially, retaining outcomes."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEMO = ROOT.parent


def main():
    plan = json.loads((ROOT / "plan.json").read_text())
    result = {"plan_sha256": hashlib.sha256((ROOT / "plan.json").read_bytes()).hexdigest(), "runs": []}
    state_path = ROOT / "execution.json"
    if state_path.exists():
        raise RuntimeError("This declared pair already has an execution record; do not overwrite it")
    state_path.write_text(json.dumps(result, indent=2) + "\n")
    for language in plan["order"]:
        command = [str(DEMO / ".venv/bin/python"), str(DEMO / "scripts/voice_to_video.py"),
                   "--instruction", plan["instructions"][language], "--view", plan["view"],
                   "--inference-seed", str(plan["inference_seed"]), "--no-open"]
        print("PAIR_START", language, flush=True)
        log = ROOT / f"{language}.log"
        with log.open("w") as output:
            process = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, timeout=1300)
        match = re.search(r"BATCH_LAUNCHED=([A-Za-z0-9_-]+)", log.read_text())
        row = {"language": language, "returncode": process.returncode,
               "run_id": match.group(1) if match else None, "command": command}
        result["runs"].append(row)
        state_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print("PAIR_FINISHED", language, row["run_id"], process.returncode, flush=True)
        if process.returncode:
            raise RuntimeError("Execution/transfer failed; retain evidence before proceeding")


if __name__ == "__main__":
    main()
