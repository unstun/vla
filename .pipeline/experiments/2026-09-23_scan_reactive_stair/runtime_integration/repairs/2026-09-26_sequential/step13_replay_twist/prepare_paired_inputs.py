"""Restore directly recorded body twist without altering old geometry or route."""
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np

HERE = Path(__file__).resolve().parent
RI = HERE.parents[2]
BASE = HERE.parent / "step6_body_reference/body_reference_030_inputs"
SOURCE = RI / "runs/walk_v4_ego/returned_artifacts/runner_output"
OUT = HERE / "body_reference_030_twist_fixed_inputs"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
old_manifest = json.loads((BASE / "input_manifest.json").read_text())
original_manifest = json.loads((RI / "replay/inputs_v4_settled/input_manifest.json").read_text())
expected_metrics = next(v for k,v in original_manifest["source"].items() if k.endswith("/metrics.jsonl"))
assert sha(SOURCE / "metrics.jsonl") == expected_metrics
origin = json.loads((SOURCE / "run_clock.json").read_text())["simulation_origin_s"]
rows = {int(round((row["sim_time_s"]+origin)*1e9)):row for row in map(json.loads,(SOURCE / "metrics.jsonl").open())}
old_events = json.loads((BASE / "events.json").read_text())
events = json.loads(json.dumps(old_events))
errors=[]
for event in events:
    if event["kind"] != "body":
        continue
    d=event["data"]; r=rows[event["stamp"]]
    for key,raw_key in (("position","base_xyz"),("quaternion","base_quat_wxyz"),
                        ("linear","base_linear_velocity_world"),("angular","base_angular_velocity_world")):
        assert d[key]==r[raw_key]
    d.update(linear_body=r["base_linear_velocity_body"],angular_body=r["base_angular_velocity_body"],twist_schema="world_and_body_v1")
    w,x,y,z=np.array(d["quaternion"])/np.linalg.norm(d["quaternion"])
    matrix=np.array([[1-2*(y*y+z*z),2*(x*y-w*z),2*(x*z+w*y)],
                     [2*(x*y+w*z),1-2*(x*x+z*z),2*(y*z-w*x)],
                     [2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)]])
    errors.append([float(np.linalg.norm(matrix @ d[name+"_body"]-d[name])) for name in ("linear","angular")])
restored=json.loads(json.dumps(events))
for event in restored:
    for key in ("linear_body","angular_body","twist_schema"):
        event["data"].pop(key,None)
assert restored==old_events and max(max(v) for v in errors)<1e-5
OUT.mkdir(exist_ok=False)
for name in ("planner.yaml","points.npz"):
    shutil.copy2(BASE / name,OUT / name)
(OUT / "events.json").write_text(json.dumps(events,indent=2)+"\n")
manifest={**old_manifest,"parent_input_manifest_sha256":sha(BASE / "input_manifest.json"),
    "recorded_twist_schema":"world_and_body_v1", "metrics_source_sha256":expected_metrics,
    "measured_start":next(e for e in events if e["kind"]=="body" and e["stamp"]==old_manifest["measured_start"]["stamp"]),
    "files":{p.name:sha(p) for p in OUT.iterdir() if p.is_file()},
    "claim":"Same recorded poses, world velocities, clouds, terrain, tracks, route and planner settings; add paired recorded body twists from the identical physics rows. Publish body twists under child_frame_id=base."}
(OUT / "input_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
result={"body_events":len(errors),"max_rotation_error_linear":max(e[0] for e in errors),
        "max_rotation_error_angular":max(e[1] for e in errors),"only_added_body_twist_fields":True,
        "parent_manifest_sha256":sha(BASE / "input_manifest.json"),"new_manifest_sha256":sha(OUT / "input_manifest.json"),
        "cloud_and_planner_hashes_unchanged":all(sha(BASE / n)==sha(OUT / n) for n in ("points.npz","planner.yaml"))}
(HERE / "INPUT_RESULT.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
