#!/usr/bin/env python3
"""Create a Python-3.8-compatible task-local copy of the official DynaNav path."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path

PINNED_COMMIT = "9fa6f8b66b9e121d5df5df071297bba8e5353ebb"
FILES = ("ticvla.py", "ticvla_vlm.py", "vision_utils.py")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def patch_python38(text: str, filename: str) -> str:
    if not text.startswith("from __future__ import annotations"):
        text = "from __future__ import annotations\n\n" + text
    if filename == "ticvla_vlm.py":
        # transformers 4.46.3 on the pinned Jetson runtime uses torch_dtype;
        # newer upstream DynaNav uses the renamed dtype keyword.
        expected = "            dtype=torch.bfloat16,"
        if expected not in text:
            raise RuntimeError("expected DynaNav dtype call not found")
        return text.replace(expected, "            torch_dtype=torch.bfloat16,", 1)
    if filename != "ticvla.py":
        return text
    replacements = {
        "Future | None": "Optional[Future]",
        "float | None": "Optional[float]",
        "Tuple[Tuple[torch.Tensor, torch.Tensor], ...] | None":
            "Optional[Tuple[Tuple[torch.Tensor, torch.Tensor], ...]]",
        "str | None": "Optional[str]",
        "int | None": "Optional[int]",
        "dict | None": "Optional[dict]",
        "torch.Tensor | None": "Optional[torch.Tensor]",
        "list[str] | None": "Optional[list[str]]",
    }
    for before, after in replacements.items():
        text = text.replace(before, after)
    if " | None" in text:
        raise RuntimeError("unhandled Python 3.10 union syntax in ticvla.py")
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    commit = subprocess.check_output(
        ["git", "-C", str(args.upstream), "rev-parse", "HEAD"], text=True
    ).strip()
    if commit != PINNED_COMMIT:
        raise RuntimeError("TIC-VLA source commit mismatch: %s" % commit)
    source = args.upstream / "DynaNav"
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = []
    for filename in FILES:
        input_path = source / filename
        output_path = args.output / filename
        output_path.write_text(patch_python38(input_path.read_text(), filename))
        manifest.append((filename, sha256(input_path), sha256(output_path)))
    for filename, pristine_hash, overlay_hash in manifest:
        print("%s pristine=%s overlay=%s" % (filename, pristine_hash, overlay_hash))


if __name__ == "__main__":
    main()
