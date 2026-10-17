"""Use the unchanged heading renderer with its underlying --limit display option."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
original = BASE / "scripts/render_heading_view.py"
limit = int(os.environ["V35_PREVIEW_FRAMES"])
if limit <= 0:
    raise ValueError("A positive preview frame limit is required")
parse_args = argparse.ArgumentParser.parse_args


def bounded_parse(parser, args=None, namespace=None):
    parsed = parse_args(parser, args, namespace)
    if hasattr(parsed, "limit") and parsed.limit is None:
        parsed.limit = limit
    return parsed


# The heading wrapper currently discards additional argv when it calls the
# renderer. Supply only its existing display-limit option; physics is unchanged.
argparse.ArgumentParser.parse_args = bounded_parse
runpy.run_path(str(original), run_name="__main__")
out = Path(os.environ["NEWTON_RUN_DIR"])
result = json.loads((out / "result.json").read_text())
camera_path = out / "heading_camera.json"
shutil.copyfile(camera_path, out / "heading_camera_original.json")
camera = json.loads(camera_path.read_text())
camera["cameras"] = camera["cameras"][:result["frames"]]
camera["frames"] = result["frames"]
camera_path.write_text(json.dumps(camera, indent=1) + "\n")
shutil.copyfile(Path(__file__), out / "executed_render_heading_preview.py")
(out / "preview_derivation.json").write_text(json.dumps({
    "display_only": True, "existing_renderer_limit": limit,
    "actual_frames": result["frames"], "source_run": result["source_run"],
    "source_states_sha256": result["source_states_sha256"],
    "original_heading_renderer_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
    "no_physics_steps": result["render_only_no_physics_steps"]}, indent=2) + "\n")
