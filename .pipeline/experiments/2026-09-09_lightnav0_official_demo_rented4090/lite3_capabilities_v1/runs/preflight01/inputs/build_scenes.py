"""Build paired arenas using the exact green-trashcan asset from ProcTHOR."""
import copy
import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET


def main():
    pkg = Path(__file__).resolve().parents[1]
    work = pkg.parent / "work/LightNav-0-lite3-capabilities-v1"
    source = work / "mujoco_demo/vln_mujoco/assets/scenes/procthor-10k-val/val_2_ceiling.xml"
    original = ET.parse(source).getroot()
    name = "ashcan_c6c85e44c01b199881223a6a35b693a4_1_0_4"
    target = copy.deepcopy(next(b for b in original.iter("body") if b.get("name") == name))
    z = target.get("pos").split()[2]
    target.set("pos", f"10.5 13.8 {z}")
    assets_by_name = {a.get("name"): a for a in original.find("asset")}
    needed = set()
    pending = [e.get(k) for e in target.iter() for k in ("mesh", "material", "texture") if e.get(k)]
    while pending:
        asset_name = pending.pop()
        if asset_name in needed:
            continue
        needed.add(asset_name)
        asset = assets_by_name[asset_name]
        pending.extend(asset.get(k) for k in ("material", "texture") if asset.get(k))
    root = ET.Element("mujoco", model="lite3_capability_arena")
    for tag in ("compiler", "option", "size", "default"):
        root.append(copy.deepcopy(original.find(tag)))
    visual = ET.SubElement(root, "visual")
    ET.SubElement(visual, "global", offwidth="480", offheight="270")
    ET.SubElement(visual, "quality", shadowsize="2048")
    ET.SubElement(visual, "headlight", ambient="0.4 0.4 0.4")
    assets = ET.SubElement(root, "asset")
    for asset in original.find("asset"):
        if asset.get("name") not in needed:
            continue
        element = copy.deepcopy(asset)
        if element.get("file"):
            absolute = (source.parent / element.get("file")).resolve()
            element.set("file", os.path.relpath(absolute, pkg / "cases"))
        assets.append(element)
    ET.SubElement(assets, "texture", name="cap_checker", type="2d", builtin="checker",
                  rgb1="0.36 0.38 0.40", rgb2="0.52 0.54 0.56", width="512", height="512")
    ET.SubElement(assets, "material", name="cap_floor", texture="cap_checker", texrepeat="10 8")
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", name="cap_light", pos="8 12 5", dir="0 0 -1",
                  directional="true", diffuse="0.8 0.8 0.8")
    common = dict(contype="8", conaffinity="15", friction="0.9 0.01 0.001")
    ET.SubElement(world, "geom", name="test_floor", type="box", pos="9.5 13.8 -0.1",
                  size="5 4 0.1", material="cap_floor", **common)
    for label, pos, size in [
        ("front", "14.5 13.8 1", "0.1 4 1"),
        ("back", "4.5 13.8 1", "0.1 4 1"),
        ("left", "9.5 17.8 1", "5 0.1 1"),
        ("right", "9.5 9.8 1", "5 0.1 1"),
    ]:
        ET.SubElement(world, "geom", name=f"test_wall_{label}", type="box", pos=pos,
                      size=size, rgba="0.70 0.72 0.76 1", **common)
    world.append(target)
    manifests = {}
    for scene in ("clear", "blocked"):
        built = copy.deepcopy(root)
        if scene == "blocked":
            ET.SubElement(built.find("worldbody"), "geom", name="test_obstacle", type="box",
                          pos="8.25 13.8 0.4", size="0.30 0.45 0.40", rgba="0.62 0.30 0.10 1",
                          **common)
        ET.indent(built, space="  ")
        data = ET.tostring(built, encoding="utf-8", xml_declaration=True)
        (pkg / "cases" / f"{scene}.xml").write_bytes(data)
        manifests[scene] = hashlib.sha256(data).hexdigest()
    (pkg / "setup/scene_manifest.json").write_text(json.dumps({
        "source_xml_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_object_body": name, "target_xyz": [10.5, 13.8, float(z)],
        "selected_asset_names": sorted(needed), "scene_sha256": manifests,
        "pair_difference": "Only the test_obstacle geom is added in blocked.xml",
    }, indent=2)+"\n")
    print(json.dumps(manifests))


if __name__ == "__main__":
    main()
