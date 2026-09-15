"""Build an isolated extension of the exact successful simulator source."""
import difflib
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError(f"Non-unique patch anchor: {old[:90]}")
    return text.replace(old, new, 1)


def main():
    records = []
    baseline_paths = []
    for line in (ROOT.parent / "manifests/successful_run_work.sha256").read_text().splitlines():
        sha, name = line.split(maxsplit=1)
        source = ROOT.parent / "work" / name
        if hashlib.sha256(source.read_bytes()).hexdigest() != sha:
            raise RuntimeError(f"Tested baseline changed: {name}")
        target = ROOT / "work" / name
        baseline_paths.append(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    name = "DynaNav/behavior/nova_carter_test_ticvla.py"
    target = ROOT / "work" / name
    original = target.read_text()
    updated = replace(original, "        # Load TIC-VLA model\n", "        self._demo = None\n        # Load TIC-VLA model\n")
    updated = updated.replace("resolution=(1920, 1080)", "resolution=(960, 540)")
    updated = replace(updated,
        '        self._camera_tp_prim_path = "/World/Robots/Nova_Carter/chassis_link/third_person_view_cam"\n',
        '        from recording_camera import select_camera, recording_resolution\n'
        '        self._camera_tp_prim_path = select_camera(stage, "/World/Robots/Nova_Carter/chassis_link/third_person_view_cam")\n')
    updated = replace(updated,
        'self._rp_tp = rep.create.render_product(self._camera_tp_prim_path, resolution=(960, 540))',
        'self._rp_tp = rep.create.render_product(self._camera_tp_prim_path, resolution=recording_resolution())')
    updated = replace(updated, "        self._capture_camera_image()\n",
        "        self._capture_camera_image()\n"
        "        if self._demo is None:\n"
        "            from demo_bridge import DemoBridge\n"
        "            self._demo = DemoBridge(self)\n"
        "        if self._demo.before_update(self):\n"
        "            self._demo.publish(self)\n"
        "            return\n")
    updated = replace(updated, "        wps = waypoints[0].float().cpu().numpy()  # (T,2) body/FLU\n",
        "        wps = waypoints[0].float().cpu().numpy()  # (T,2) body/FLU\n"
        "        self._demo.capture_plan(wps, robot_pose, current_step)\n")
    updated = replace(updated,
        "                'cache_available': bool(kv_cache_available), 'waypoints': wps.tolist(),\n",
        "                'instruction': instruction,\n"
        "                'cache_available': bool(kv_cache_available), 'waypoints': wps.tolist(),\n")
    updated = replace(updated,
        "                action = self._diff.forward(command=np.array([final_v, final_w], dtype=np.float32))\n",
        "                final_v, final_w = self._demo.guard_command(final_v, final_w)\n"
        "                action = self._diff.forward(command=np.array([final_v, final_w], dtype=np.float32))\n")
    updated = replace(updated, "        # Stream data and log\n",
        "        self._demo.publish(self, final_v, final_w)\n"
        "        # Stream data and log\n")
    updated = replace(updated, "        print(\"[on_stop] Called\")\n",
        "        print(\"[on_stop] Called\")\n"
        "        if self._demo is not None:\n"
        "            self._demo.close()\n"
        "            self._demo = None\n")
    target.write_text(updated)
    (ROOT / "manifests/interactive.patch").write_text("".join(difflib.unified_diff(
        original.splitlines(keepends=True), updated.splitlines(keepends=True),
        fromfile="a/" + name, tofile="b/" + name)))
    for source in [*sorted((ROOT / "scripts").glob("*.py")), *sorted((ROOT / "scripts").glob("*.sh")), *sorted((ROOT / "web").glob("*")),
                   *baseline_paths, ROOT / "hospital_demo.yaml"]:
        if source.is_file():
            records.append({"path": str(source.relative_to(ROOT)),
                            "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    (ROOT / "manifests/source.json").write_text(json.dumps(records, indent=2) + "\n")
    print("DEMO_SOURCE_READY", len(records))


if __name__ == "__main__":
    main()
