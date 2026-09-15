#!/usr/bin/env python3
"""Create and hash the frozen deterministic image fixtures."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

from audit_contract import canonical_bytes, sha256_file


def build(repo_root: Path, experiment_root: Path) -> dict:
    inputs = experiment_root / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    sources = {
        "real_lite3": repo_root
        / ".pipeline/experiments/2026-08-19_omnivla_lite3_receive_only/runs/real_original/20260819T103300.657356Z_61711107-9e58-4341-9c47-80e2b40f086d/frame.jpg",
        "upstream_sample": repo_root
        / "third_party/2026-08-18_omnivla_5182600/OmniVLA/inference/current_img.jpg",
    }
    outputs = {
        "real_lite3": inputs / "real_lite3.jpg",
        "upstream_sample": inputs / "upstream_sample.jpg",
        "real_lite3_mirror": inputs / "real_lite3_mirror.png",
        "real_lite3_blur": inputs / "real_lite3_blur.png",
    }
    shutil.copyfile(sources["real_lite3"], outputs["real_lite3"])
    shutil.copyfile(sources["upstream_sample"], outputs["upstream_sample"])
    with Image.open(sources["real_lite3"]) as image:
        rgb = image.convert("RGB")
        ImageOps.mirror(rgb).save(outputs["real_lite3_mirror"], format="PNG")
        rgb.filter(ImageFilter.GaussianBlur(radius=4.0)).save(
            outputs["real_lite3_blur"], format="PNG"
        )
    images = {}
    transforms = {
        "real_lite3": {"name": "none", "source": str(sources["real_lite3"])},
        "upstream_sample": {"name": "none", "source": str(sources["upstream_sample"])},
        "real_lite3_mirror": {
            "name": "Pillow ImageOps.mirror",
            "source_image_id": "real_lite3",
        },
        "real_lite3_blur": {
            "name": "Pillow GaussianBlur",
            "radius": 4.0,
            "source_image_id": "real_lite3",
        },
    }
    for image_id, path in outputs.items():
        with Image.open(path) as image:
            width, height = image.size
        images[image_id] = {
            "id": image_id,
            "path": "inputs/%s" % path.name,
            "sha256": sha256_file(path),
            "width": width,
            "height": height,
            "transform": transforms[image_id],
        }
    expected = "c982be19a4b55213252902c4cc957a7e74903a6f253fc2378f512e0051237f09"
    if images["real_lite3"]["sha256"] != expected:
        raise RuntimeError("real Lite3 fixture identity mismatch")
    manifest = {"schema_version": 1, "images": images}
    (experiment_root / "fixtures.json").write_bytes(canonical_bytes(manifest))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--experiment-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.repo_root.resolve(), args.experiment_root.resolve()), indent=2))


if __name__ == "__main__":
    main()

