"""Register a flat support prior with no obstacle/actor information in PCT."""
import hashlib
import json
from pathlib import Path
import pickle
import sys

import numpy as np
from materialize import BASE, HERE


def main():
    # PCT runs in the pinned ROS image with NumPy 1.x. Generate its pickle
    # there; NumPy 2.x writes private module paths that NumPy 1.x cannot load.
    if int(np.__version__.split(".")[0]) != 1:
        raise RuntimeError("Run this generator in the pinned native ROS image (NumPy 1.x)")
    out = HERE / "flat_inputs_v2"
    out.mkdir(exist_ok=False)
    data = np.zeros((5,2,101,101), dtype=np.float32)
    data[4] = 3.
    with (out / "flat_floor.pickle").open("wb") as stream:
        pickle.dump({"data":data,"resolution":.1,"center":[0.,0.],"slice_h0":.5,"slice_dh":.5},stream,protocol=4)
    original = json.loads((BASE / "inputs/stair_scenario.json").read_text())
    scene = {"schema_version":1,"mode":"walk","spawn_ground_xyz_m":[0.,0.,0.],
             "spawn_body_height_m":.35,"spawn_yaw_rad":0.,"goal_ground_xyz_m":[3.,0.,0.],
             "locomotion_reference_height_m":.3,"nominal_body_height_m":.35,
             "max_sim_seconds":35.,"max_wall_seconds":900.,"camera":original["camera"],
             "navigation_input":"flat support prior and actual geometric LiDAR; no actor or obstacle metadata",
             "human_truth":"physics/rendering/scoring only"}
    (out / "scene.json").write_text(json.dumps(scene,indent=2)+'\n')
    (out / "generation.json").write_text(json.dumps({"numpy_version": np.__version__,
        "python_version": sys.version, "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "environment": "pinned ROS Humble image, same NumPy runtime as native PCT"}, indent=2)+'\n')
    manifest={"files":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()},
              "claim":"Synthetic flat support prior in the existing PCT format; all obstacles come from live sensor returns. No occupied/free obstacle map is injected."}
    (out / "manifest.json").write_text(json.dumps(manifest,indent=2)+'\n')
    source = BASE / "runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_publisher.py"
    text = source.read_text().replace("from pct_sim_clock_core import", "from lite3_sim_bridge.pct_sim_clock_core import")
    anchor='\n\nclass PctSimClockPublisher(Node):'
    loader='''

def load_registered_flat_map(path):
    import json
    import pickle
    root = Path(__file__).resolve().parent / "flat_inputs_v2"
    manifest = json.loads((root / "manifest.json").read_text())
    if path.resolve() != (root / "flat_floor.pickle").resolve():
        raise ValueError("Unregistered flat map path")
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["files"]["flat_floor.pickle"]:
        raise ValueError("Flat support map identity mismatch")
    with path.open("rb") as handle:
        return pickle.load(handle)
'''
    text=text.replace(anchor,loader+anchor).replace('source = load_pinned_map(map_path)','source = load_registered_flat_map(map_path)')
    target=HERE/'flat_support_publisher.py';target.write_text(text)
    (HERE/'flat_publisher_identity.json').write_text(json.dumps({'source':str(source),
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'change':'Registered flat map loader and qualified import only; existing projection, clock gate, ROS publisher and metadata unchanged.'},indent=2)+'\n')
    print(out)


if __name__ == '__main__':
    main()
