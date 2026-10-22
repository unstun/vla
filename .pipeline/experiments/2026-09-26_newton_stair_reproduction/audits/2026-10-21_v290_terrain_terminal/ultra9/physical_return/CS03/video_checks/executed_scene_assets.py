"""Original Building triangles and skinning of the original official human."""
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from pxr import Gf, Usd, UsdGeom, UsdSkel, Vt

BASE = Path(__file__).resolve().parents[1]
PROJECT = BASE.parents[2]
ARCHIVE = PROJECT / ".pipeline/experiments/2026-09-23_scan_reactive_stair/runtime_integration/runs/walk_scan28_height030_right_v1"
sys.path.insert(0, str(BASE / "references"))
sys.path.insert(0, str(ARCHIVE / "bridge"))
import official_building_human as official
from lite3_sim_bridge import run_isaac_v12_fallback as original_v12
from lite3_sim_bridge.mid360_pattern import load_mid360_pattern


def verify_inputs():
    identity = json.loads((BASE / "setup/source_identity.json").read_text())
    for item in identity["inputs"]:
        if hashlib.sha256((BASE / item["path"]).read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Archived input changed: {item['path']}")
    bridge = ARCHIVE / "bridge/lite3_sim_bridge"
    identity["bridge_python_sha256"] = {
        str(p.relative_to(bridge)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in bridge.rglob("*.py")}
    return identity


def building_mesh():
    path = BASE / "inputs/building.usda"
    expected = json.loads((BASE / "inputs/stair_scenario.json").read_text())
    route = json.loads((BASE / "inputs/actor_route.json").read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest() != route["building_usda_sha256"]:
        raise ValueError("Building hash mismatch")
    stage = Usd.Stage.Open(str(path))
    meshes = [UsdGeom.Mesh(p) for p in stage.Traverse() if p.IsA(UsdGeom.Mesh)]
    if len(meshes) != 1 or UsdGeom.GetStageMetersPerUnit(stage) != 1 or UsdGeom.GetStageUpAxis(stage) != "Z":
        raise ValueError("Unexpected Building mesh/unit/axis contract")
    mesh = meshes[0]
    points = np.array(mesh.GetPointsAttr().Get(), dtype=np.float64)
    transform = np.array(UsdGeom.Xformable(mesh).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    vertices = (np.c_[points, np.ones(len(points))] @ transform)[:, :3].astype(np.float32)
    counts = np.array(mesh.GetFaceVertexCountsAttr().Get())
    if not np.all(counts == 3):
        raise ValueError("Expected original triangle-only Building mesh")
    faces = np.array(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int32).reshape(-1, 3)
    return vertices, faces, expected


class OfficialHuman:
    """Evaluate existing retarget animation; no procedural gait or proxy mesh."""
    def __init__(self, output):
        self.provenance = official.verify_official_bundle(BASE / "inputs/official_human", BASE / "inputs/official_human/cache")
        building_sha = hashlib.sha256((BASE / "inputs/building.usda").read_bytes()).hexdigest()
        self.route = official.load_actor_route(BASE / "inputs/actor_route.json", building_sha)
        self.animations = original_v12._load_official_human_animation_cache(BASE / "inputs/official_human/cache/official_human_retarget_cache.npz")
        if self.animations["content_sha256"] != official.CACHE_CONTENT_SHA:
            raise ValueError("Official animation content mismatch")
        path = Path(output) / "official_skinning.usda"
        self.wrapper = official.make_visual_wrapper(path, BASE / "inputs/official_human/male_adult_police_04.usd",
                                                   BASE / "inputs/official_human/cache/official_human_retarget_cache.npz", original_v12)
        self.stage = Usd.Stage.Open(str(path))
        self.animation = UsdSkel.Animation(self.stage.GetPrimAtPath("/HumanVisual/OfficialAnimations/Active"))
        skeleton = next(UsdSkel.Skeleton(p) for p in self.stage.Traverse() if p.IsA(UsdSkel.Skeleton))
        self.cache = UsdSkel.Cache()
        for p in self.stage.Traverse():
            if p.IsA(UsdSkel.Root):
                self.cache.Populate(UsdSkel.Root(p), Usd.PrimDefaultPredicate)
        self.skeleton_query = self.cache.GetSkelQuery(skeleton)
        if not self.skeleton_query:
            raise RuntimeError("Official skeleton query unavailable")
        self.meshes = []
        offset = 0
        indices = []
        for p in self.stage.Traverse():
            if not p.IsA(UsdGeom.Mesh):
                continue
            mesh = UsdGeom.Mesh(p)
            query = self.cache.GetSkinningQuery(p)
            if not query:
                raise RuntimeError(f"Official skinning query unavailable: {p.GetPath()}")
            points = mesh.GetPointsAttr().Get()
            counts = np.array(mesh.GetFaceVertexCountsAttr().Get())
            if not np.all(counts == 3):
                raise ValueError("Official mesh is not triangle-only")
            face = np.array(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int32).reshape(-1, 3)
            self.meshes.append((str(p.GetPath()), query, points, face))
            indices.append(face + offset)
            offset += len(points)
        self.faces = np.concatenate(indices)
        self.vertex_count = offset
        self.skeleton_world = np.array(UsdGeom.Xformable(skeleton).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))

    def vertices(self, elapsed, *, fixed_frame=None, fixed_root=None):
        state = official.actor_state(self.route, float(elapsed))
        pose = official.visual_pose(state)
        clip = "walk" if state["phase"] == "walking" else "idle"
        frame = (int(float(elapsed) * self.animations["fps"]) if fixed_frame is None else fixed_frame)
        frame %= len(self.animations[clip + "_translations"])
        translations, rotations = original_v12._official_human_usd_components(
            self.animations[clip + "_translations"][frame], self.animations[clip + "_rotations_xyzw"][frame])
        self.animation.GetTranslationsAttr().Set(translations)
        self.animation.GetRotationsAttr().Set(rotations)
        transforms = self.skeleton_query.ComputeSkinningTransforms(Usd.TimeCode.Default())
        parts = []
        for _, query, original, _ in self.meshes:
            points = Vt.Vec3fArray(original)
            if not query.ComputeSkinnedPoints(transforms, points, Usd.TimeCode.Default()):
                raise RuntimeError("Official skin deformation failed")
            values = np.array(points, dtype=np.float64)
            parts.append((np.c_[values, np.ones(len(values))] @ self.skeleton_world)[:, :3])
        local = np.concatenate(parts)
        root = pose["visual_root_xyz_m"] if fixed_root is None else fixed_root
        yaw = pose["visual_yaw_radians"]
        c, s = math.cos(yaw), math.sin(yaw)
        rotation = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        world = (local @ rotation.T + np.array(root)).astype(np.float32)
        if world.shape != (self.vertex_count, 3) or not np.isfinite(world).all():
            raise ValueError("Invalid skinned vertex output")
        return world, {"state": state, "pose": pose, "clip": clip, "frame": frame}
