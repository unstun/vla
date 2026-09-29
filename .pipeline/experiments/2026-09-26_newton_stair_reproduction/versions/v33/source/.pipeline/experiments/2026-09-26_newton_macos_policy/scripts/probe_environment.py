"""Check actual imports/device and installed Newton source identity."""
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform

BASE = Path(__file__).resolve().parents[1]
OUT = Path(os.environ["NEWTON_RUN_DIR"])

import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")
import newton
import mujoco
import mujoco_warp
import onnx
from warp_nn.runtime import OnnxRuntime

source = BASE / "source/newton-c2ca70bec5998062b0b2d35869865cbe3a49feee/newton"
installed = Path(newton.__file__).parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
matches = {}
for path in source.rglob("*.py"):
    relative = path.relative_to(source)
    target = installed / relative
    matches[str(relative)] = target.is_file() and sha(target) == sha(path)
assert all(matches.values()), [p for p, same in matches.items() if not same]
assert wp.get_device().is_cpu
packages = {p: metadata.version(p) for p in
            ("newton", "warp-lang", "mujoco", "mujoco-warp", "warp-nn", "onnx", "numpy", "pyglet", "imgui-bundle", "usd-core")}
result = {"platform": platform.platform(), "python": platform.python_version(),
          "packages": packages, "device": str(wp.get_device()),
          "installed_python_source_files": len(matches), "source_matches_pinned_tag": True,
          "claim": "Import and CPU environment readiness only; no dynamics or policy run."}
(OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
