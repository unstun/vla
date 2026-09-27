"""Qualify original scene and official skin deformation independently of ROS."""
import json
import os
from pathlib import Path
import shutil

import numpy as np
from scene_assets import OfficialHuman, building_mesh, verify_inputs

out = Path(os.environ["NEWTON_RUN_DIR"])
for name in ("scene_assets.py", "probe_assets.py"):
    shutil.copyfile(Path(__file__).with_name(name), out / ("executed_" + name))
identity = verify_inputs()
(out / "source_identity.json").write_text(json.dumps(identity, indent=2) + "\n")
building, faces, scenario = building_mesh()
human = OfficialHuman(out)
first, _ = human.vertices(10.1, fixed_frame=0, fixed_root=(0, 0, 0))
second, _ = human.vertices(10.1, fixed_frame=30, fixed_root=(0, 0, 0))
repeat, _ = human.vertices(10.1, fixed_frame=0, fixed_root=(0, 0, 0))
displacement = np.linalg.norm(second - first, axis=1)
if float(displacement.max()) <= .01 or not np.array_equal(first, repeat):
    raise ValueError("Skin deformation or fixed-frame repeat control failed")
np.savez_compressed(out / "mesh_controls.npz", building_vertices=building, building_faces=faces,
                    human_first=first, human_second=second, human_faces=human.faces)
result = {"building_vertices": len(building), "building_triangles": len(faces),
          "human_meshes": len(human.meshes), "human_vertices": human.vertex_count,
          "human_triangles": len(human.faces), "fixed_root_vertex_motion_max_m": float(displacement.max()),
          "fixed_root_vertex_motion_mean_m": float(displacement.mean()), "identical_frame_repeat": True,
          "first_bounds": [first.min(axis=0).tolist(), first.max(axis=0).tolist()],
          "accepted": True, "claim": "Exact source geometry and CPU official skinning only; no sensor/physics outcome."}
(out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2), flush=True)
