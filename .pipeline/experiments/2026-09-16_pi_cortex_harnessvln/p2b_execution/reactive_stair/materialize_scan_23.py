"""Bound layer association using the existing step-height capability."""
import json
from pathlib import Path
import shutil

from materialize_scan_20 import sha

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_22"
OUT = HERE.parent / "builds/scan_23"


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or json.loads((BASE / "build_result.json").read_text()).get("passed") is not True:
        raise ValueError("scan_22 source/build identity gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    target = OUT / "src/plan_env/include/plan_env/eth_step_score_adaptation.h"
    shutil.copy2(HERE / target.name, target)
    manifest = {"base": "scan_22", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
                "changed_sha256": {str(target.relative_to(OUT)): sha(target)},
                "change": "Both scoring passes require same-level nearest surfaces within the existing critical step height; missing compatible neighbors propagate Unknown",
                "preserved": "All numeric thresholds, unknown blocking, search, spline, selected ground and raw cloud inputs, and tracker",
                "claim": "Conservative layer-label repair; cannot increase the free set or alone resolve no-path",
                "generator_sha256": sha(Path(__file__))}
    (OUT / "same_level_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
