"""Offline, render-only MuJoCo overhead view. No stepping, no policy, no control."""
from __future__ import annotations

CEILING_PREFIX = "ceiling_"
# Verified preset from continuation_v3/research/static_probe_02/result.json.
LOOKAT = (8.8, 11.5, 0.0)
DISTANCE = 12.0
AZIMUTH = 90.0
ELEVATION = -90.0
VERTICAL_SPAN_M = 7.0


def make_overhead_renderer(model, width: int = 1024, height: int = 768,
                           vertical_span_m: float = VERTICAL_SPAN_M,
                           lookat=LOOKAT):
    """Return (renderer, camera, hidden_geoms). Only named ceilings are hidden."""
    import mujoco

    model.vis.global_.offwidth = max(int(model.vis.global_.offwidth), width)
    model.vis.global_.offheight = max(int(model.vis.global_.offheight), height)
    hidden = []
    for gid in range(model.ngeom):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gid) or ""
        if name.startswith(CEILING_PREFIX):
            hidden.append({"id": gid, "name": name})
            model.geom_rgba[gid, 3] = 0.0
    camera = mujoco.MjvCamera()
    mujoco.mjv_defaultCamera(camera)
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.orthographic = 1
    camera.lookat[:] = list(lookat)
    camera.distance = DISTANCE
    camera.azimuth = AZIMUTH
    camera.elevation = ELEVATION
    model.vis.global_.orthographic = 1
    model.vis.global_.fovy = float(vertical_span_m)
    renderer = mujoco.Renderer(model, height=height, width=width)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    renderer.update_scene(data, camera=camera)
    renderer.render()
    if int(renderer.scene.camera[0].orthographic) != 1:
        renderer.close()
        raise RuntimeError("effective GL projection is not orthographic")
    return renderer, camera, hidden


def world_to_pixel(x, y, width, height, vertical_span_m=VERTICAL_SPAN_M, lookat=LOOKAT):
    """Orthographic world->image mapping for the preset above (image origin top-left)."""
    horizontal_span = vertical_span_m * width / height
    u = (x - lookat[0]) / horizontal_span * width + width / 2.0
    v = height / 2.0 - (y - lookat[1]) / vertical_span_m * height
    return u, v


def body_local_to_world(capture_pose, forward, left):
    """Robot-local [forward,left] -> world XY using the CAPTURE pose."""
    import math
    x, y, yaw = capture_pose
    return (x + math.cos(yaw) * forward - math.sin(yaw) * left,
            y + math.sin(yaw) * forward + math.cos(yaw) * left)
