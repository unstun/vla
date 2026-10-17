"""Add measured foreground tracking with a pinned static prior and full ground."""
import json
from pathlib import Path
import shutil

from materialize_scan_20 import once, sha

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_21"
OUT = HERE.parent / "builds/scan_22"


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or json.loads((BASE / "build_result.json").read_text()).get("passed") is not True:
        raise ValueError("scan_21 source/build identity gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    package = OUT / "src/scan_reactive_tracker"
    module = package / "scan_reactive_tracker"
    names = {"moving_cluster_io.py": "io.py", "static_background.py": "static_background.py",
             "static_foreground_tracker.py": "static_foreground_tracker.py",
             "physical_ground_contract.py": "physical_ground_contract.py"}
    changed = []
    for source_name, target_name in names.items():
        text = (HERE / source_name).read_text().replace("from moving_cluster_core import ", "from scan_reactive_tracker.core import ")
        text = text.replace("from static_background import ", "from scan_reactive_tracker.static_background import ")
        target = module / target_name
        target.write_text(text)
        changed.append(target)
    node = module / "node.py"
    once(node, "import math", "import math\nfrom pathlib import Path")
    once(node, "from scan_reactive_tracker.core import (CloudFrame, MovingClusterTracker,",
         "from scan_reactive_tracker.core import (CloudFrame,")
    once(node, "from scan_reactive_tracker.io import decode_float32_cloud, terrain_from_pct_records",
         "from scan_reactive_tracker.io import decode_float32_cloud, terrain_from_pct_records\n"
         "from scan_reactive_tracker.static_background import load_building_background\n"
         "from scan_reactive_tracker.static_foreground_tracker import StaticForegroundTracker as MovingClusterTracker\n"
         "from scan_reactive_tracker.physical_ground_contract import (PHYSICAL_GROUND_TOPIC, MAX_GROUND_POINTS, verify_physical_ground)")
    once(node, "        self._tracker = MovingClusterTracker()", '''        background_path = str(self.declare_parameter("static_background_pcd", "").value)
        if not background_path:
            raise ValueError("a pinned static Building background is required")
        background = load_building_background(Path(background_path))
        self._tracker = MovingClusterTracker(background)
        self.get_logger().info("Tracking prior: " + background.source_id + "; current-source=" + self._tracker.SOURCE_ID)''')
    once(node, 'self.create_subscription(PointCloud2, "/pct_tomogram", self._on_terrain, pct_qos)',
         'self.create_subscription(PointCloud2, PHYSICAL_GROUND_TOPIC, self._on_terrain, pct_qos)')
    once(node, '''            records = decode_float32_cloud(
                bytes(msg.data), msg.width, msg.height, msg.point_step, msg.row_step,
                msg.is_bigendian, self._fields(msg), ("x", "y", "z", "intensity")
            )''', '''            fields = self._fields(msg)
            verify_physical_ground(bytes(msg.data), msg.header.frame_id, msg.width, msg.height,
                                   msg.point_step, msg.row_step, msg.is_bigendian, fields)
            records = decode_float32_cloud(
                bytes(msg.data), msg.width, msg.height, msg.point_step, msg.row_step,
                msg.is_bigendian, fields, ("x", "y", "z", "intensity"),
                max_points=MAX_GROUND_POINTS
            )''')
    once(node, "                records, bytes(msg.data), msg.header.frame_id, stamp_ns(msg.header.stamp)",
         "                records, bytes(msg.data), msg.header.frame_id, stamp_ns(msg.header.stamp), cost_limit=None")
    once(node, "    def _publish(self, snapshot: Snapshot):\n        msg = TrackedPersonSnapshot()", '''    def _publish(self, snapshot: Snapshot):
        status = (snapshot.complete, snapshot.reason)
        if getattr(self, "_last_logged_status", None) != status:
            self.get_logger().info("track_status complete=%s reason=%s metrics=%s" %
                                   (snapshot.complete, snapshot.reason, self._tracker.last_background_metrics))
            self._last_logged_status = status
        msg = TrackedPersonSnapshot()''')
    once(node, "the static /pct_tomogram publisher.", "the independent /tracker_ground publisher and pinned static PCD prior.")
    changed.append(node)
    # Dependency wheel is staged and hash-verified per execution package. The
    # unchanged Foxy NumPy is retained; no build-time network resolution occurs.
    once(package / "package.xml", "  <exec_depend>rclpy</exec_depend>",
         "  <exec_depend>rclpy</exec_depend>\n  <exec_depend>python3-numpy</exec_depend>\n  <exec_depend>python3-scipy</exec_depend>")
    changed.append(package / "package.xml")
    manifest = {"base": "scan_21", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
                "changed_sha256": {str(p.relative_to(OUT)): sha(p) for p in changed},
                "source_id": "sensor_lidar_static_background_cluster_v3",
                "change": "Tracker-only pinned static foreground, independent exact physical-ground payload, explicit coverage failure",
                "preserved": "Original current XY clustering and association core; all raw SCAN clouds, occupancy rules, search/controller/optimizer and unknown blocking",
                "execution_requirements": "Pinned Building PCD, verified SciPy 1.8.1 CPython38 wheel, and /tracker_ground 149504-record payload",
                "generator_sha256": sha(Path(__file__))}
    (OUT / "foreground_tracker_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
