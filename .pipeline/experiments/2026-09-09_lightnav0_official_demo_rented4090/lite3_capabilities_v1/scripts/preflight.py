"""Compile/render cases and test physical contact telemetry before model trials."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from PIL import Image

from metrics import displacement
from vln_mujoco.robots.lite3 import Lite3Backend


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exp", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    pkg = args.exp / "lite3_capabilities_v1"
    base = args.exp / "lite3_v1"
    args.out.mkdir(parents=True, exist_ok=False)
    checks = {}
    suite = json.loads((pkg / "cases/suite.json").read_text())
    for case in suite["cases"]:
        encoded = json.dumps(case, ensure_ascii=False).encode("utf-8")
        returned = json.loads(encoded)
        checks[case["id"]+"_verbatim"] = (
            returned["instruction"] == case["instruction"]
            and hashlib.sha256(returned["instruction"].encode()).hexdigest() == case["instruction_sha256"])
    clear = ET.parse(pkg / "cases/clear.xml").getroot()
    blocked = ET.parse(pkg / "cases/blocked.xml").getroot()
    world = blocked.find("worldbody")
    obstacle = world.find("geom[@name='test_obstacle']")
    world.remove(obstacle)
    ET.indent(clear, space="  ")
    ET.indent(blocked, space="  ")
    checks["only_box_differs"] = ET.tostring(clear) == ET.tostring(blocked)
    measured = displacement((5, 4, math.pi/2), (5, 6, math.pi/2))
    checks["body_frame_distance"] = abs(measured["forward_m"]-2)<1e-9 and abs(measured["lateral_m"])<1e-9
    checks["backwards_is_negative"] = displacement((0,0,0), (-1,0,0))["forward_m"] == -1
    scene_results = {}
    for scene in ("clear", "blocked"):
        robot = Lite3Backend(base / "assets/lite3/lite3.xml", base / "policy/policy_stateless_h10.onnx",
                             scene_source=pkg / "cases" / f"{scene}.xml")
        for _ in range(400):
            robot.step((0.0, 0.0))
        state = robot.state()
        checks[scene+"_stands"] = state.pose[2] > 0.15 and state.telemetry["tilt_rad"] < 0.3
        checks[scene+"_no_false_obstacle_contacts"] = robot.obstacle_contact_steps == 0
        renderer = mujoco.Renderer(robot.model, height=270, width=480)
        renderer.update_scene(robot.data, camera=robot.camera_name)
        Image.fromarray(renderer.render()).save(args.out / f"front_{scene}.png")
        renderer.update_scene(robot.data, camera=robot.third_person_camera(mujoco.MjvCamera()))
        Image.fromarray(renderer.render()).save(args.out / f"chase_{scene}.png")
        renderer.close()
        scene_results[scene] = {"pose": state.pose, "scene": robot.scene_metadata,
                                "target_xyz": robot.data.body("ashcan_c6c85e44c01b199881223a6a35b693a4_1_0_4").xpos.tolist()}
        if scene == "blocked":
            robot.data.qpos[robot.base_qpos:robot.base_qpos+3] = [8.25,13.8,0.35]
            mujoco.mj_forward(robot.model, robot.data)
            robot._observe_contacts()
            checks["injected_overlap_detected"] = robot.obstacle_contact_steps > 0
            robot.reset()
            checks["contact_counters_reset"] = robot.obstacle_contact_steps == 0 and robot.maximum_obstacle_force == 0
        else:
            start = robot.state().pose
            for _ in range(400):
                robot.step((0.4, 0.0))
            checks["forward_locomotion_in_arena"] = robot.state().pose[0] - start[0] > 0.3
        checks[scene+"_finite"] = bool(np.isfinite(robot.data.qpos).all())
    result = {"checks": checks, "passed": all(checks.values()), "scenes": scene_results,
              "new_lightnav_calls": 0, "collision_probe": "static overlap fixture outside evaluation episodes"}
    (args.out / "result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2), flush=True)
    raise SystemExit(not result["passed"])


if __name__ == "__main__":
    main()
