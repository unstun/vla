"""Static visualization feasibility probe; no policy, control or simulation step."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault("MUJOCO_GL", "egl")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    source = Path(args.source).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(source / "mujoco_demo"))
    import mujoco
    import numpy as np
    from PIL import Image
    from vln_mujoco.robots.turtlebot import TurtleBotBackend

    started = time.monotonic()
    robot = TurtleBotBackend()
    model, data = robot.model, robot.data
    model.vis.global_.offwidth = 1024
    model.vis.global_.offheight = 768
    signature = mujoco.mjtState.mjSTATE_INTEGRATION
    state = np.empty(mujoco.mj_stateSize(model, signature), dtype=np.float64)
    mujoco.mj_getState(model, data, state, signature)
    clone = mujoco.MjData(model)
    mujoco.mj_setState(model, clone, state, signature)
    mujoco.mj_forward(model, clone)
    restored = np.empty_like(state)
    mujoco.mj_getState(model, clone, restored, signature)
    assert np.array_equal(state, restored)
    np.save(out / "static_state.npy", state)

    with mujoco.Renderer(model, height=270, width=480) as renderer:
        renderer.update_scene(data, camera=robot.camera_name)
        front_before = renderer.render().copy()
        Image.fromarray(front_before).save(out / "front_native.png")
        free = mujoco.MjvCamera()
        mujoco.mjv_defaultCamera(free)
        renderer.update_scene(data, camera=robot.third_person_camera(free))
        Image.fromarray(renderer.render()).save(out / "third_person_native.png")

    original_alpha = model.geom_rgba[:, 3].copy()
    hidden = []
    for gid in range(model.ngeom):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gid) or ""
        if name.startswith("ceiling_"):
            hidden.append({"id": gid, "name": name})
            model.geom_rgba[gid, 3] = 0.0
    assert len(hidden) == 10
    camera = mujoco.MjvCamera()
    mujoco.mjv_defaultCamera(camera)
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.orthographic = 1
    camera.lookat[:] = [8.8, 11.5, 0.0]
    camera.distance = 12.0
    camera.azimuth = 90.0
    camera.elevation = -90.0
    model.vis.global_.fovy = 7.0
    with mujoco.Renderer(model, height=768, width=1024) as renderer:
        renderer.update_scene(clone, camera=camera)
        Image.fromarray(renderer.render()).save(out / "topdown_static.png")
        gl = renderer.scene.camera[0]
        projection = {k: np.asarray(getattr(gl, k)).tolist()
                      for k in ["pos", "forward", "up", "frustum_width", "frustum_bottom",
                                "frustum_top", "frustum_near", "frustum_far", "orthographic"]}
    model.geom_rgba[:, 3] = original_alpha
    with mujoco.Renderer(model, height=270, width=480) as renderer:
        renderer.update_scene(data, camera=robot.camera_name)
        front_after = renderer.render().copy()
    assert np.array_equal(front_before, front_after), "Restoring visualization changed the native view"
    mujoco.mj_getState(model, data, restored, signature)
    assert np.array_equal(state, restored)
    assert data.time == 0.0 and clone.time == 0.0
    result = dict(kind="static_render_feasibility_only", new_vla_inference=False,
                  simulation_steps=0, mujoco=mujoco.__version__, state_signature=int(signature),
                  state_size=len(state), exact_state_roundtrip=True,
                  native_front_unchanged_after_restore=True, elapsed_seconds=time.monotonic()-started,
                  source=str(source), hidden_offline_ceiling_geoms=hidden,
                  camera=dict(lookat=[8.8,11.5,0],distance=12,azimuth=90,elevation=-90,
                              orthographic=True,vertical_span_m=7,width=1024,height=768),
                  projection=projection,
                  files={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in out.iterdir() if p.is_file()})
    (out / "result.json").write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__ == "__main__":
    main()
