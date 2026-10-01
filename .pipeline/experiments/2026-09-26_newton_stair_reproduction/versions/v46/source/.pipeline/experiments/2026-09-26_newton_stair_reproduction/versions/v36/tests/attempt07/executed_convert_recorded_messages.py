"""Validate old CDR against recorded JSON, then adapt only the ROS wire schema."""
from pathlib import Path
import argparse
import hashlib
import json

from rclpy.serialization import deserialize_message, serialize_message
from rosidl_runtime_py.convert import message_to_ordereddict
from rosidl_runtime_py.set_message import set_message_fields
from scan_planner_msgs.msg import Bspline, P2BRoute

parser=argparse.ArgumentParser()
parser.add_argument("--mode",choices=("verify_old","convert_new"),required=True)
args=parser.parse_args()
archive=Path("/archive/audits/2026-09-29_corridor_entry")
out=Path("/attempt")
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
for state in ("v33_stand","v32_stand"):
    source=archive/state/"inputs"
    folder=out/state
    folder.mkdir(exist_ok=True)
    records=[]
    if args.mode=="convert_new":
        destination=folder/"converted_inputs"
        destination.mkdir()
        for path in source.iterdir():
            if path.name not in ("spline.cdr","route.cdr"):
                (destination/path.name).symlink_to(path)
    for name,kind in (("spline",Bspline),("route",P2BRoute)):
        data=json.loads((source/(name+".json")).read_text())["data"]
        if args.mode=="verify_old":
            decoded=deserialize_message((source/(name+".cdr")).read_bytes(),kind)
            assert dict(message_to_ordereddict(decoded))==data,(state,name,"old CDR/JSON mismatch")
        else:
            message=kind()
            set_message_fields(message,data)
            fields=dict(message_to_ordereddict(message))
            assert {key:fields[key] for key in data}==data,(state,name,"recorded fields changed")
            if name=="spline":assert message.emergency_stop is False
            else:assert message.has_goal_pose is False
            target=destination/(name+".cdr")
            target.write_bytes(serialize_message(message))
            decoded=deserialize_message(target.read_bytes(),kind)
            decoded_fields=dict(message_to_ordereddict(decoded))
            assert {key:decoded_fields[key] for key in data}==data
        record={"name":name,"old_cdr_sha256":sha(source/(name+".cdr")),"recorded_json_sha256":sha(source/(name+".json")),
                "recorded_fields_unchanged":True,"mode":args.mode}
        if args.mode=="convert_new":record["new_cdr_sha256"]=sha(target)
        records.append(record)
    (folder/(args.mode+".json")).write_text(json.dumps(records,indent=2)+"\n")
print("Recorded message identity passed:",args.mode)
