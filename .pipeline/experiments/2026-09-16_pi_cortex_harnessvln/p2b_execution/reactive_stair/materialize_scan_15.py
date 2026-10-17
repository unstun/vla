"""Restore the existing vertical cost gradient for the 3D stair candidate."""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_14"
OUT = HERE.parent / "builds/scan_15"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if expected != actual or json.loads((BASE / "build_result.json").read_text()).get("passed") is not True:
        raise ValueError("scan_14 source/build gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    path = OUT / "src/bspline_opt/src/bspline_optimizer.cpp"
    source = path.read_bytes()
    old = b'    grad_3D.row(2).setZero();\r\n'
    if source.count(old) != 2:
        raise ValueError("expected rebound and refine vertical-gradient freezes")
    path.write_bytes(source.replace(old, b'    // Preserve the computed Z gradient so supported stair height can change.\r\n'))
    manifest = {"base": "scan_14", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
                "changed_sha256": {str(path.relative_to(OUT)): sha(path)},
                "problem": "Rebound and refinement explicitly zeroed the computed Z gradient, freezing the initial endpoint-interpolated height",
                "change": "Use all three components of the existing smoothness, collision, fitness and feasibility gradients",
                "preserved": "cost terms and weights, initial/end derivatives, common collision query, physical limit and final safety checks"}
    (OUT / "vertical_optimizer_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
