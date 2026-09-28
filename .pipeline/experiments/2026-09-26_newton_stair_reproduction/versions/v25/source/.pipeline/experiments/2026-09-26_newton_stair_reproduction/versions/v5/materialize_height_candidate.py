"""Create one hash-gated candidate with explicit optional Z optimization."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

BASE = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = BASE / "runtime/scan43_prefix_diagnostic_v2"
TARGET = BASE / "runtime/scan44_height_v5"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace(data, old, new, count=1):
    if data.count(old) != count:
        raise ValueError("Pinned optimizer anchor mismatch")
    return data.replace(old, new)


def main():
    for name in ("source_sha256.json", "install_sha256.json"):
        for path, expected in json.loads((SOURCE / name).read_text()).items():
            if sha(SOURCE / path) != expected:
                raise ValueError("Parent identity changed: " + path)
    TARGET.mkdir(exist_ok=False)
    shutil.copytree(SOURCE / "src", TARGET / "src")
    cpp = TARGET / "src/bspline_opt/src/bspline_optimizer.cpp"
    header = TARGET / "src/bspline_opt/include/bspline_opt/bspline_optimizer.h"
    data = cpp.read_bytes()
    anchor = b'    order_ = static_cast<int>(node->get_parameter("optimization.order").as_int());'
    addition = b'''
    if (!node->has_parameter("optimization.optimize_height"))
      node->declare_parameter<bool>("optimization.optimize_height", false);
    optimize_height_ = node->get_parameter("optimization.optimize_height").as_bool();
    RCLCPP_INFO(node->get_logger(), "height_optimization=%s; terrain and final trajectory gates retained",
                optimize_height_ ? "enabled" : "fixed");'''
    data = replace(data, anchor, anchor + addition)
    data = replace(data, b"    grad_3D.row(2).setZero();",
                   b"    if (!optimize_height_) grad_3D.row(2).setZero();", count=2)
    cpp.write_bytes(data)
    header.write_bytes(replace(header.read_bytes(), b"    int order_;",
                              b"    bool optimize_height_ = false; // Explicit terrain-constrained profile only.\r\n    int order_;"))
    manifest = {str(p.relative_to(TARGET)):sha(p) for p in (TARGET / "src").rglob("*") if p.is_file()}
    (TARGET / "source_sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
    identity = {"source_sha256":manifest,"baseline":str(SOURCE),"integration_version":"v5",
                "change":"Optional Z optimization in existing rebound/refinement; false preserves fixed-height behavior"}
    (BASE / "repairs/2026-09-26_generic_occupancy/candidate44_height_v5_identity.json").write_text(json.dumps(identity,indent=2)+"\n")
    diff = []
    for path in (cpp,header):
        relative = path.relative_to(TARGET)
        diff.extend(difflib.unified_diff((SOURCE/relative).read_text().splitlines(True),path.read_text().splitlines(True),
                                       fromfile="v4/"+str(relative),tofile="v5/"+str(relative),n=0))
    (HERE / "native_changes.patch").write_text("".join(diff))
    shutil.copyfile(__file__, TARGET / "executed_materialize.py")
    print(json.dumps({"candidate":str(TARGET),"source_files":len(manifest),"changed_files":[str(p.relative_to(TARGET)) for p in (cpp,header)]}))


if __name__ == "__main__":
    main()
