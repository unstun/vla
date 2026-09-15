"""Resume the task shard with the already-tested TIC-VLA range downloader."""
import json
from pathlib import Path
import subprocess
import sys
from download_assets import download_in_ranges, sha256

root = Path(__file__).resolve().parents[1]
source = json.loads((root / "setup/model_source.json").read_text())
shard = next(x for x in source["siblings"] if x["rfilename"].endswith(".safetensors"))
target = root / "checkpoints/LightNav-0" / shard["rfilename"]
partial = target.with_name(target.name + ".part")
item = {"destination": str(target.relative_to(root)), "bytes": shard["size"],
        "url": f"https://huggingface.co/{source['id']}/resolve/{source['sha']}/{shard['rfilename']}"}
print(json.dumps({"resumed_bytes":partial.stat().st_size,"total_bytes":item["bytes"],"workers":4}),flush=True)
download_in_ranges(item, partial, workers=4)
assert partial.stat().st_size == shard["size"]
assert sha256(partial) == shard["lfs"]["sha256"]
partial.replace(target)
subprocess.run([sys.executable,str(root / "scripts/download_checkpoint.py"),
                str(root / "setup/model_source.json"),str(target.parent),
                str(root / "setup/checkpoint_manifest.json"),"--verify-only"],check=True)
