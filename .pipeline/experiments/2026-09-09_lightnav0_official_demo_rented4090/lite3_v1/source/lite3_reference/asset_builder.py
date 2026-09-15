"""Generate a RoboGauge-compatible MJCF from the pinned official Lite3 MJCF."""

from __future__ import annotations

import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import math

from .runtime import sha256_file
from .source_pins import (
    ACTUATOR_NAMES,
    DEEP_ROBOTICS_MODEL,
    EFFORT_LIMITS,
    FOOT_GEOM_NAMES,
    JOINT_NAMES,
    OFFICIAL_LITE3_MESH_SHA256,
    OFFICIAL_LITE3_MJCF_SHA256,
    SPAWN_HEIGHT_M,
)


ALLOWED_TRANSFORMS = (
    "remove vendor demo floor and light from robot worldbody",
    "rename root body TORSO and its contact-exclusion references to base_link for RoboGauge attachment",
    "set root body spawn height to the frozen v12 value 0.35 m",
    "remove standalone freejoint because RoboGauge adds the attached root freejoint",
    "bind the visual default to the vendor-defined default_material for dm_control attachment",
    "name existing IMU sensors and add ordered joint position, velocity, and actuator-force sensors",
    "set per-joint actuator ctrlrange to v12 Hip 24 Nm and Knee 36 Nm limits",
    "replace shank mesh collision with the two v12 training URDF cylinders so contact"
    " classification matches the trained policy's effective collision (visual mesh kept;"
    " SIM-EVAL-01: shank.STL reaches z=-0.2326, below the foot sphere bottom -0.2321,"
    " so a quiet stand falsely reported shank contact)",
)

# v12 training shank collision, verbatim from resources/lite3/urdf/lite3.urdf:
# two z-axis cylinders in the shank (knee) frame, pitched about Y.
# MJCF cylinder size = (radius, half-length); quat = (cos(p/2), 0, sin(p/2), 0).
_SHANK_TRAINING_CYLINDERS = (
    # (name suffix, pos, pitch rad, radius, full length)
    ("", (0.005, 0.0, -0.03), -0.2, 0.015, 0.12),
    ("_lower", (0.01, 0.0, -0.14), 0.15, 0.015, 0.10),
)
_SHANK_LEG_PREFIXES = ("FL", "FR", "HL", "HR")


def _require_one(root: ET.Element, path: str) -> ET.Element:
    matches = root.findall(path)
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one XML element at {path!r}, found {len(matches)}.")
    return matches[0]


def build_asset(source_xml: Path, output_xml: Path, manifest_path: Path) -> dict:
    source_xml = source_xml.resolve()
    output_xml = output_xml.resolve()
    manifest_path = manifest_path.resolve()
    if sha256_file(source_xml) != OFFICIAL_LITE3_MJCF_SHA256:
        raise ValueError(f"Official Lite3 MJCF hash mismatch: {source_xml}")

    source_mesh_dir = source_xml.parent / "meshes"
    for name, expected in OFFICIAL_LITE3_MESH_SHA256.items():
        actual = sha256_file(source_mesh_dir / name)
        if actual != expected:
            raise ValueError(f"Official Lite3 mesh hash mismatch for {name}: expected {expected}, got {actual}.")

    tree = ET.parse(source_xml)
    root = tree.getroot()
    if root.tag != "mujoco" or root.get("model") != "Lite3":
        raise ValueError("Unexpected official Lite3 MJCF root contract.")
    root.set("model", "lite3")

    visual_default = _require_one(root, "./default/default/default[@class='visual']/geom")
    visual_default.set("material", "default_material")

    worldbody = _require_one(root, "./worldbody")
    for child in list(worldbody):
        if child.tag == "geom" and child.get("name") == "floor":
            worldbody.remove(child)
        elif child.tag == "light":
            worldbody.remove(child)

    base = _require_one(worldbody, "./body[@name='TORSO']")
    base.set("name", "base_link")
    base.set("pos", f"0 0 {SPAWN_HEIGHT_M:.8g}")
    for freejoint in list(base.findall("./freejoint")):
        base.remove(freejoint)

    for exclusion in root.findall("./contact/exclude"):
        for attribute in ("body1", "body2"):
            if exclusion.get(attribute) == "TORSO":
                exclusion.set(attribute, "base_link")
    dangling_torso_refs = [
        (element.tag, attribute)
        for element in root.iter()
        for attribute, value in element.attrib.items()
        if value == "TORSO"
    ]
    if dangling_torso_refs:
        raise ValueError(f"Unconverted TORSO references remain after root rename: {dangling_torso_refs}")

    replaced_shanks = []
    for leg in _SHANK_LEG_PREFIXES:
        shank_body = _require_one(root, f".//body[@name='{leg}_SHANK']")
        mesh_collisions = [
            geom
            for geom in shank_body.findall("./geom")
            if geom.get("name") == f"{leg}_SHANK_collision" and geom.get("type") == "mesh"
        ]
        if len(mesh_collisions) != 1:
            raise ValueError(
                f"Expected exactly one mesh collision geom on {leg}_SHANK, found {len(mesh_collisions)}."
            )
        insert_at = list(shank_body).index(mesh_collisions[0])
        shank_body.remove(mesh_collisions[0])
        for suffix, pos, pitch, radius, length in _SHANK_TRAINING_CYLINDERS:
            half, p = length / 2.0, pitch / 2.0
            cylinder = ET.Element(
                "geom",
                {
                    "name": f"{leg}_SHANK_collision{suffix}",
                    "type": "cylinder",
                    "pos": f"{pos[0]:.8g} {pos[1]:.8g} {pos[2]:.8g}",
                    "quat": f"{math.cos(p):.8g} 0 {math.sin(p):.8g} 0",
                    "size": f"{radius:.8g} {half:.8g}",
                    "class": "collision",
                },
            )
            shank_body.insert(insert_at, cylinder)
            insert_at += 1
        replaced_shanks.append(leg)
    if replaced_shanks != list(_SHANK_LEG_PREFIXES):
        raise ValueError(f"Shank collision replacement incomplete: {replaced_shanks}")

    foot_geom_names = {geom.get("name") for geom in root.iter("geom")}
    missing_feet = [name for name in FOOT_GEOM_NAMES if name not in foot_geom_names]
    if missing_feet:
        raise ValueError(f"Foot contact geom index must be non-empty, missing: {missing_feet}")

    actuator = _require_one(root, "./actuator")
    motors = actuator.findall("./motor")
    if [motor.get("joint") for motor in motors] != list(JOINT_NAMES):
        raise ValueError("Official Lite3 actuator order no longer matches the frozen v12 joint order.")
    if [motor.get("name") for motor in motors] != list(ACTUATOR_NAMES):
        raise ValueError("Official Lite3 actuator names no longer match the frozen contract.")
    for motor, effort_limit in zip(motors, EFFORT_LIMITS, strict=True):
        motor.set("ctrllimited", "true")
        motor.set("ctrlrange", f"{-effort_limit:.8g} {effort_limit:.8g}")

    sensor = _require_one(root, "./sensor")
    for element in sensor:
        if element.tag == "framequat":
            element.set("name", "imu_quat")
        elif element.tag == "framelinvel":
            element.set("name", "imu_lin_vel")
        elif element.tag == "accelerometer":
            element.set("name", "imu_acc")
        elif element.tag == "gyro":
            element.set("name", "imu_gyro")

    ordered_sensors: list[ET.Element] = []
    for tag, suffix in (("jointpos", "pos"), ("jointvel", "vel"), ("jointactuatorfrc", "torque")):
        for joint_name in JOINT_NAMES:
            attributes = {"name": f"{joint_name}_{suffix}", "joint": joint_name}
            ordered_sensors.append(ET.Element(tag, attributes))
    sensor[:] = ordered_sensors + list(sensor)

    output_xml.parent.mkdir(parents=True, exist_ok=True)
    output_mesh_dir = output_xml.parent / "meshes"
    output_mesh_dir.mkdir(parents=True, exist_ok=True)
    for name in OFFICIAL_LITE3_MESH_SHA256:
        shutil.copy2(source_mesh_dir / name, output_mesh_dir / name)

    ET.indent(tree, space="  ")
    tree.write(output_xml, encoding="utf-8", xml_declaration=True)
    manifest = {
        "schema_version": 1,
        "source": {
            "name": DEEP_ROBOTICS_MODEL.name,
            "url": DEEP_ROBOTICS_MODEL.url,
            "commit": DEEP_ROBOTICS_MODEL.commit,
            "path": "Lite3/mjcf/Lite3.xml",
            "sha256": OFFICIAL_LITE3_MJCF_SHA256,
        },
        "mesh_sha256": OFFICIAL_LITE3_MESH_SHA256,
        "output": {
            "path": output_xml.name,
            "sha256": sha256_file(output_xml),
        },
        "allowed_transforms": list(ALLOWED_TRANSFORMS),
        "joint_order": list(JOINT_NAMES),
        "actuator_order": list(ACTUATOR_NAMES),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
