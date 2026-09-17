"""Record non-secret execution facts and a hash manifest for local sync-back."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess


root = Path(__file__).resolve().parents[1]
setup = root / "setup"


def command(argv):
    proc = subprocess.run(argv, text=True, capture_output=True, check=False)
    return {"argv": argv, "exit": proc.returncode, "stdout": proc.stdout,
            "stderr": proc.stderr}


source = root / "source/AgentCanvas"
facts = {
    "recorded_utc": datetime.now(timezone.utc).isoformat(),
    "host": socket.gethostname(), "root": str(root),
    "credential_present_in_audit_shell": bool(os.environ.get("DEEPSEEK_API_KEY")),
    "gpu": command(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used",
                    "--format=csv,noheader"]),
    "compute_processes": command(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
                                  "--format=csv,noheader"]),
    "disk": command(["df", "-h", str(root)]),
    "memory": command(["free", "-h"]),
    "simulator_listener": command(["ss", "-ltn", "sport", "=", ":19200"]),
    "repositories": {},
    "pip_checks": {},
    "helper": {
        "local_source": ".pipeline/experiments/2026-09-09_lightnav0_5070ti_inference/scripts/download_assets.py",
        "execution_path": str(root / "dependencies/download_assets.py"),
        "sha256": hashlib.sha256((root / "dependencies/download_assets.py").read_bytes()).hexdigest(),
    },
}
for name, path in [("AgentCanvas", source), ("VLN-CE", source / "third_party/VLN-CE"),
                   ("habitat-lab", source / "third_party/habitat-lab")]:
    facts["repositories"][name] = {
        "commit": command(["git", "-C", str(path), "rev-parse", "HEAD"]),
        "status": command(["git", "-C", str(path), "status", "--short"])}
for env in ["agentcanvas", "ac-vlnce"]:
    facts["pip_checks"][env] = command(
        [f"/home/sun/miniconda3/envs/{env}/bin/python", "-m", "pip", "check"])
(setup / "runtime_inventory.json").write_text(json.dumps(facts, indent=2) + "\n")
files = []
for path in sorted(setup.rglob('*')):
    if path.is_file() and path.name != "returned_artifacts.sha256":
        files.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root)}\n")
(setup / "returned_artifacts.sha256").write_text(''.join(files))
print(json.dumps({"recorded_files": len(files), "runtime_inventory": str(setup / "runtime_inventory.json")}))
