"""Runtime layout and source-integrity checks for generated evaluation state."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .source_pins import DEEP_ROBOTICS_MODEL, GO2_RL_GYM, ROBOGAUGE, SourcePin


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RuntimeLayout:
    root: Path
    robogauge: Path
    go2_rl_gym: Path
    deep_robotics_model: Path
    generated_asset: Path
    asset_manifest: Path
    v9_terrain_dir: Path
    v9_terrain_manifest: Path
    v9_d075_terrain_dir: Path
    v9_d075_terrain_manifest: Path


def get_runtime_layout() -> RuntimeLayout:
    root = Path(os.environ.get("LITE3_ROBOGAUGE_RUNTIME", PROJECT_ROOT / ".runtime")).expanduser().resolve()
    return RuntimeLayout(
        root=root,
        robogauge=root / "sources" / "RoboGauge",
        go2_rl_gym=root / "sources" / "go2_rl_gym",
        deep_robotics_model=root / "sources" / "DeepRoboticsModel",
        generated_asset=root / "assets" / "lite3" / "lite3_robogauge.xml",
        asset_manifest=root / "assets" / "lite3" / "asset_manifest.json",
        v9_terrain_dir=root / "assets" / "terrains" / "v9_rough_d050_seed42",
        v9_terrain_manifest=root / "assets" / "terrains" / "v9_rough_d050_seed42" / "terrain_manifest.json",
        v9_d075_terrain_dir=root / "assets" / "terrains" / "v9_rough_d075_seed42",
        v9_d075_terrain_manifest=(
            root / "assets" / "terrains" / "v9_rough_d075_seed42" / "terrain_manifest.json"
        ),
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def verify_checkout(path: Path, pin: SourcePin) -> None:
    if not (path / ".git").is_dir():
        raise RuntimeError(f"Missing runtime checkout for {pin.name}: {path}")
    actual = git_head(path)
    if actual != pin.commit:
        raise RuntimeError(f"{pin.name} commit mismatch: expected {pin.commit}, got {actual}.")
    status = subprocess.run(
        ["git", "-C", str(path), "status", "--short", "--untracked-files=no"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise RuntimeError(f"Tracked files in {pin.name} runtime checkout are modified:\n{status}")


def _verify_terrain_manifest(
    terrain_dir: Path,
    manifest_path: Path,
    *,
    expected_difficulty: float,
) -> None:
    if not manifest_path.is_file():
        raise RuntimeError("Generated v9 terrain assets are missing; run scripts/build_v9_terrain_assets.py.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_terrains = {
        "pyramid_stairs",
        "boxes",
        "random_rough",
        "pyramid_slope",
        "pyramid_slope_inv",
    }
    if manifest.get("difficulty") != expected_difficulty:
        raise RuntimeError(
            f"Generated v9 terrain difficulty mismatch for {manifest_path}: "
            f"expected={expected_difficulty}, actual={manifest.get('difficulty')}."
        )
    if manifest.get("seed") != 42 or set(manifest.get("terrains", ())) != expected_terrains:
        raise RuntimeError(f"Generated v9 terrain protocol mismatch: {manifest_path}")
    if not manifest.get("outputs"):
        raise RuntimeError(f"Generated v9 terrain manifest has no hashed outputs: {manifest_path}")
    for relative_path, expected_sha256 in manifest.get("outputs", {}).items():
        path = terrain_dir / relative_path
        if not path.is_file():
            raise RuntimeError(f"Generated v9 terrain file is missing: {path}")
        actual_sha256 = sha256_file(path)
        if actual_sha256 != expected_sha256:
            raise RuntimeError(
                f"Generated v9 terrain hash mismatch for {path}: "
                f"expected={expected_sha256}, actual={actual_sha256}."
            )


def verify_runtime_sources(layout: RuntimeLayout | None = None) -> RuntimeLayout:
    layout = get_runtime_layout() if layout is None else layout
    verify_checkout(layout.robogauge, ROBOGAUGE)
    verify_checkout(layout.go2_rl_gym, GO2_RL_GYM)
    verify_checkout(layout.deep_robotics_model, DEEP_ROBOTICS_MODEL)
    if not layout.generated_asset.is_file() or not layout.asset_manifest.is_file():
        raise RuntimeError("Generated Lite3 RoboGauge asset is missing; run scripts/bootstrap_runtime.py.")
    _verify_terrain_manifest(
        layout.v9_terrain_dir,
        layout.v9_terrain_manifest,
        expected_difficulty=0.5,
    )
    _verify_terrain_manifest(
        layout.v9_d075_terrain_dir,
        layout.v9_d075_terrain_manifest,
        expected_difficulty=0.75,
    )
    return layout
