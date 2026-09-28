"""Acquire the release-pinned upstream Go2 assets before policy execution."""
import hashlib
import json
import os
from pathlib import Path

import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
import newton
from newton._src.utils.download_assets import NEWTON_ASSETS_REF, NEWTON_ASSETS_URL

path = newton.utils.download_asset("unitree_go2")
records = {str(p.relative_to(path)): {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                                   "bytes": p.stat().st_size}
           for p in sorted(path.rglob("*")) if p.is_file()}
assert "rl_policies/mjw_go2.onnx" in records
assert "rl_policies/go2.yaml" in records
result = {"repository": NEWTON_ASSETS_URL, "commit": NEWTON_ASSETS_REF,
          "directory": str(path), "files": records,
          "claim": "Pinned asset/model acquisition only; no inference or physics."}
(Path(os.environ["NEWTON_RUN_DIR"]) / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"directory": str(path), "commit": NEWTON_ASSETS_REF,
                  "files": len(records), "bytes": sum(p["bytes"] for p in records.values())}, indent=2))
