"""Prepare ABI bytes from pinned config and verified caller defaults, locally."""

import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent


def prepare():
    snapshot = ROOT / "private_snapshot"
    for manifest in ("source_manifest.json", "dependency_manifest.json", "algorithm_inputs_manifest.json"):
        for record in json.loads((ROOT / manifest).read_text())["files"]:
            relative = Path(record["local_path"])
            original = (ROOT.parents[2] / relative if relative.parts[0] == ".pipeline"
                        else ROOT / relative)
            if hashlib.sha256(original.read_bytes()).hexdigest() != record["sha256"]:
                raise ValueError("Original factory input changed: " + relative.name)
    fields = json.loads((ROOT / "analysis/abi_summary.json").read_text())["MotionConfig"]["fields"]
    # GetAlgorithmConfig, executable 0x30a18..0x30bcc and 0x315e8..0x316dc.
    defaults = {f["name"]: False if f["dwarf_type"] == "bool" else 0.0 for f in fields}
    for f in fields:
        if 64 <= f["offset"] <= 96:
            defaults[f["name"]] = 70.0
        if 104 <= f["offset"] <= 128:
            defaults[f["name"]] = 71.0
    defaults.update(stand_height=0.33, backflip_hl_hip_kp_comp=1.0,
                    backflip_hr_hip_kp_comp=1.0, kp_carpet_comp=10.0,
                    stand_kd=1.2, forward_kd=0.7)
    executable = (snapshot / "bin/jy_exe").read_bytes()
    defaults["backward_kd"] = struct.unpack_from("<d", executable, 0xbaf80)[0]
    # This file contains only scalar keys; parse exactly, without a YAML/TOML dependency.
    override = {}
    for line in (snapshot / "conf/Algorithm.toml").read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key not in defaults:
            raise ValueError("unknown MotionConfig field: " + key)
        override[key] = value == "true" if value in ("true", "false") else float(value)
    defaults.update(override)
    data = bytearray(216)
    for field in fields:
        struct.pack_into("<?" if field["dwarf_type"] == "bool" else "<d",
                         data, field["offset"], defaults[field["name"]])
    prepared = snapshot / "algorithm_input"
    prepared.mkdir(exist_ok=True)
    (prepared / "motion_config.bin").write_bytes(data)
    config = json.loads((snapshot / "conf/deeprcs.json").read_text())["this_robot"]
    name = config["module_name"] + "-" + config["serial_number"]
    (prepared / "identity.txt").write_text(name + "\n" + config["type"] + "\n")
    summary = {"fields": defaults, "sha256": hashlib.sha256(data).hexdigest(),
               "identity_source": "private_snapshot/conf/deeprcs.json:this_robot",
               "caller": "main 0x1b184..0x1b1a4; GetFullName 0x1ccbc; InitialKinetics 0x31bc8"}
    (ROOT / "analysis/algorithm_input_config.json").write_text(json.dumps(summary, indent=2) + "\n")
    return prepared


if __name__ == "__main__":
    print(prepare())
