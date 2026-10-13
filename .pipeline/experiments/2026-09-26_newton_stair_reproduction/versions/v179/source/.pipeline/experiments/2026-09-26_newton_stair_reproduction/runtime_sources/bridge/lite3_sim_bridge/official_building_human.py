"""Official Isaac human asset and simulator-truth schedule for a Building candidate.

The schedule is simulator truth only. It is never a tracked-person publisher or
planner input. Isaac imports are inside make_visual_wrapper(), after AppLauncher.
The USD authoring below adapts the pinned bridge's official visual wrapper:
references/upstream/2026-09-16_lite3_isaac_harness_backend, whose
lite3_sim_bridge/package.xml declares Apache-2.0. NVIDIA character bytes
remain under NVIDIA's separate materials terms.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


CHARACTER_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/"
    "People/Characters/male_adult_police_04/male_adult_police_04.usd"
)
BIPED_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/"
    "People/Characters/Biped_Setup.usd"
)
ASSET_HASHES = {
    "male_adult_police_04.usd": "3110909a21152d10bfcdf16d4e49653bae196d3093efe61a2099b4ee1761733b",
    "textures/male_adult_police_04_BaseColor.png": "7713714d56db66cec13e98cc5197d41bd5008ebe6f43c57bfc0ba0272b55ed88",
    "textures/male_adult_police_04_Normal.png": "8e8cd9850a091e961c6f7ee8a5e0ee8d462399c3122014461e218a47e014891e",
    "textures/male_adult_police_04_ORM.png": "3251967eb0bf6046afc02da3256baae6349299a710a4c14a5a9a5fa540fef279",
}
CACHE_FILE_SHA = "ac58a683fe9dd85ec3ad0266c7653b289dc1dd9b256d2abac0cc96ac7e45cfcb"
CACHE_MANIFEST_SHA = "51e1b0a84cc489f38c69b79b17176a5d7fd2f119ee42cada66f56b272be412db"
CACHE_CONTENT_SHA = "76c19b57ebd03e01820e6b9db79bde8f2f3e436302744ef457278af8d17ef5b3"
VISUAL_ROOT = "/World/OfficialHumanVisual"
SOURCE_FOOT_Z_M = -1.9355964298028994e-7
SOURCE_VISIBLE_TOP_Z_M = 1.7357525825500488
SOURCE_FORWARD_YAW_RAD = -math.pi / 2.0
# No stair actor route has passed the Building/PCT geometry and clearance gate.
# A later reviewed source candidate must pin that route's exact bytes here.
APPROVED_ROUTE_SHA256 = '2cf70439b8f4566809dd679d505d023cda581305034146ec3fa610a3343e73bb'


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_official_bundle(asset_root: Path, cache_dir: Path) -> dict:
    """Reject missing/mutated official bytes before starting Isaac."""
    asset_root, cache_dir = Path(asset_root), Path(cache_dir)
    for rel, expected in ASSET_HASHES.items():
        path = asset_root / rel
        if not path.is_file() or file_sha256(path) != expected:
            raise ValueError(f"official human asset missing or changed: {rel}")
    manifest_path = cache_dir / "official_human_retarget_cache.json"
    cache_path = cache_dir / "official_human_retarget_cache.npz"
    if not manifest_path.is_file() or file_sha256(manifest_path) != CACHE_MANIFEST_SHA:
        raise ValueError("official human cache manifest missing or changed")
    if not cache_path.is_file() or file_sha256(cache_path) != CACHE_FILE_SHA:
        raise ValueError("official human retarget cache missing or changed")
    manifest = json.loads(manifest_path.read_text())
    expected = {
        "schema_version": 1,
        "character_url": CHARACTER_URL,
        "biped_url": BIPED_URL,
        "joint_count": 101,
        "fps": 30,
        "idle_frame_count": 60,
        "walk_frame_count": 90,
        "cache_file_sha256": CACHE_FILE_SHA,
        "cache_content_sha256": CACHE_CONTENT_SHA,
        "local_procedural_gait": False,
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError("official human retarget cache provenance changed")
    return {
        "character_usd": str((asset_root / "male_adult_police_04.usd").resolve()),
        "cache_npz": str(cache_path.resolve()),
        "asset_sha256": ASSET_HASHES.copy(),
        "cache_file_sha256": CACHE_FILE_SHA,
        "cache_content_sha256": CACHE_CONTENT_SHA,
        "source": "NVIDIA Isaac Sim 5.1 male_adult_police_04 + Biped retarget replay",
    }


def load_actor_route(path: Path, building_sha256: str,
                     approved_sha256: str | None = APPROVED_ROUTE_SHA256) -> dict:
    """Read a separately geometry-reviewed actor route; never guess stairs."""
    if approved_sha256 is None:
        raise ValueError("official human stair route has no approved SHA-256")
    if file_sha256(path) != approved_sha256:
        raise ValueError("official human stair route SHA-256 mismatch")
    payload = json.loads(Path(path).read_text())
    if payload.get("schema_version") != 1 or payload.get("frame_id") != "world":
        raise ValueError("official human route schema/frame mismatch")
    if payload.get("building_usda_sha256") != building_sha256:
        raise ValueError("official human route Building source mismatch")
    if payload.get("geometry_reviewed") is not True:
        raise ValueError("official human route has no geometry review")
    raw = payload.get("waypoints_ground_xyz_m")
    if not isinstance(raw, list) or len(raw) < 2:
        raise ValueError("official human route needs at least two ground waypoints")
    points = []
    for row in raw:
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError("official human route waypoint shape invalid")
        xyz = tuple(float(value) for value in row)
        if not all(math.isfinite(value) for value in xyz):
            raise ValueError("official human route waypoint is not finite")
        points.append(xyz)
    lengths = [math.dist(a[:2], b[:2]) for a, b in zip(points, points[1:])]
    if any(length <= 0.0 or length > 0.25 for length in lengths):
        raise ValueError("official human ground waypoints must progress by at most 0.25 m XY")
    if any(abs(b[2] - a[2]) > 0.26 for a, b in zip(points, points[1:])):
        raise ValueError("official human ground waypoints exceed the V12 step height")
    speed = float(payload.get("speed_mps", 0.0))
    delay = float(payload.get("start_delay_s", -1.0))
    if not (math.isfinite(speed) and 0.05 <= speed <= 1.0 and
            math.isfinite(delay) and delay >= 0.0):
        raise ValueError("official human speed/delay invalid")
    return {"points": points, "lengths": lengths, "distance_m": sum(lengths),
            "speed_mps": speed, "start_delay_s": delay,
            "route_sha256": file_sha256(path)}


def actor_state(route: dict, elapsed_s: float) -> dict:
    """Current simulator actor pose only; callers must not publish this as a track."""
    if not math.isfinite(elapsed_s) or elapsed_s < 0.0:
        raise ValueError("actor simulation time invalid")
    distance = min(max(elapsed_s - route["start_delay_s"], 0.0)
                   * route["speed_mps"], route["distance_m"])
    remaining = distance
    segment = len(route["lengths"]) - 1
    for index, length in enumerate(route["lengths"]):
        if remaining <= length or index == segment:
            segment = index
            break
        remaining -= length
    a, b = route["points"][segment:segment + 2]
    fraction = min(1.0, remaining / route["lengths"][segment])
    ground = tuple(a[i] + fraction * (b[i] - a[i]) for i in range(3))
    yaw = math.atan2(b[1] - a[1], b[0] - a[0])
    phase = ("waiting" if elapsed_s < route["start_delay_s"] else
             "arrived" if distance >= route["distance_m"] else "walking")
    return {"ground_xyz_m": ground, "yaw_rad": yaw, "phase": phase,
            "distance_m": distance, "elapsed_s": elapsed_s}


def make_visual_wrapper(path: Path, character_usd: Path, cache_npz: Path, v12) -> dict:
    """Author a local-reference official skeleton; preserve the USD asset bytes."""
    from pxr import Sdf, Usd, UsdGeom, UsdSkel

    cache = v12._load_official_human_animation_cache(cache_npz)
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/HumanVisual")
    stage.SetDefaultPrim(root.GetPrim())
    character = UsdGeom.Xform.Define(stage, "/HumanVisual/OfficialCharacter")
    character.GetPrim().GetReferences().AddReference(str(Path(character_usd).resolve()))
    skeleton_prims = [prim for prim in stage.Traverse()
                      if prim.GetTypeName() == "Skeleton"]
    if len(skeleton_prims) != 1:
        raise RuntimeError(f"official character skeleton count: {len(skeleton_prims)}")
    skeleton = UsdSkel.Skeleton(skeleton_prims[0])
    joints = tuple(str(value) for value in skeleton.GetJointsAttr().Get())
    rest_transforms = skeleton.GetRestTransformsAttr().Get()
    if joints != cache["joints"] or len(rest_transforms) != len(joints):
        raise RuntimeError("official character skeleton disagrees with Biped cache")
    _, _, rest_scales = UsdSkel.DecomposeTransforms(rest_transforms)
    target_path = Sdf.Path("/HumanVisual/OfficialAnimations/Active")
    target = UsdSkel.Animation.Define(stage, target_path)
    target.CreateJointsAttr(list(joints))
    translations, rotations = v12._official_human_usd_components(
        cache["idle_translations"][0], cache["idle_rotations_xyzw"][0])
    target.CreateTranslationsAttr(translations)
    target.CreateRotationsAttr(rotations)
    target.CreateScalesAttr(rest_scales)
    UsdSkel.BindingAPI.Apply(skeleton_prims[0]).CreateAnimationSourceRel().SetTargets([target_path])
    stage.GetRootLayer().Save()
    return {"path": str(path.resolve()), "sha256": file_sha256(path),
            "character_usd": str(Path(character_usd).resolve()),
            "cache_sha256": CACHE_FILE_SHA, "joint_count": len(joints),
            "reference_kind": "local_official_usd"}


def visual_pose(state: dict) -> dict:
    ground = state["ground_xyz_m"]
    yaw = state["yaw_rad"] - SOURCE_FORWARD_YAW_RAD
    return {
        "visual_root_xyz_m": (ground[0], ground[1], ground[2] + 0.02 - SOURCE_FOOT_Z_M),
        "visual_quaternion_wxyz": (math.cos(yaw / 2.0), 0.0, 0.0, math.sin(yaw / 2.0)),
        "visual_foot_world_z_m": ground[2] + 0.02,
        "visual_top_world_z_m": ground[2] + 0.02 - SOURCE_FOOT_Z_M + SOURCE_VISIBLE_TOP_Z_M,
        "capsule_bottom_world_z_m": None,
        "foot_to_capsule_bottom_error_m": None,
        "visual_yaw_radians": yaw,
    }
