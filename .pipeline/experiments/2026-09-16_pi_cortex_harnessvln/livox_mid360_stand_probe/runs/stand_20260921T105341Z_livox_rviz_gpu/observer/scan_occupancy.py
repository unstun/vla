"""Start scan_04 occupancy plus Lite3 URDF TF helpers beside a stand_probe.

Reuses the two-goal SCAN remap and native_rviz_review nodes. Does not start
closed_loop_controller, PCT, or a new detector.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess


RELATIVE_MESH_PREFIX = 'filename="./meshes/'
SCAN_PLANNER_REMAPS = (
    "body_pose:=/quad_0/body_pose",
    "sensor_pose:=/quad_0/lidar_pose",
    "cloud:=/quad_0/cloud",
)
FORBIDDEN_HELPER_TOKENS = (
    "closed_loop_controller",
    "euclidean",
    "clusterer",
    "cluster_node",
)


def rewrite_urdf_meshes(source_description, urdf_path):
    if RELATIVE_MESH_PREFIX not in source_description:
        raise ValueError("Lite3 URDF does not contain the expected relative mesh prefix")
    absolute_mesh_prefix = 'filename="file://{}/meshes/'.format(Path(urdf_path).parent)
    return source_description.replace(RELATIVE_MESH_PREFIX, absolute_mesh_prefix)


def helper_inner_script():
    remaps = " ".join("-r %s" % item for item in SCAN_PLANNER_REMAPS)
    return r"""set -eo pipefail
source /opt/ros/foxy/setup.bash
source /workspace/install/setup.bash
export ROS_LOCALHOST_ONLY=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/bridge:${PYTHONPATH:-}
ros2 pkg prefix robot_state_publisher >/dev/null
python3 - <<'PY'
from pathlib import Path
urdf = Path("/robot/lite3_pro_sensor_rig_real_with_interface.urdf")
text = urdf.read_text(encoding="utf-8")
prefix = 'filename="./meshes/'
if prefix not in text:
    raise SystemExit("Lite3 URDF does not contain the expected relative mesh prefix")
Path("/logs/lite3_rviz.urdf").write_text(
    text.replace(prefix, 'filename="file://{}/meshes/'.format(urdf.parent)),
    encoding="utf-8",
)
PY
ros2 run robot_state_publisher robot_state_publisher /logs/lite3_rviz.urdf --ros-args -r joint_states:=/quad_0/joint_states -p use_sim_time:=true > /logs/robot_state_publisher.log 2>&1 &
rsp_pid=$!
python3 -c "from lite3_sim_bridge.rviz_replay_node import main; main()" --ros-args -p source_mode:=live -p frame_id:=world -p robot_root_frame:=TORSO -p sample_count:=160 -p audit_path:=/logs/review_audit.jsonl -p preload_first_snapshot:=false -p require_live_lidar:=true -p use_sim_time:=true > /logs/rviz_replay_node.log 2>&1 &
replay_pid=$!
ros2 run scan_planner scan_planner_node --ros-args --params-file /config/planner.yaml """ + remaps + r""" > /logs/scan_planner_node.log 2>&1 &
scan_pid=$!
cleanup() {
  kill "$scan_pid" "$replay_pid" "$rsp_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
while kill -0 "$scan_pid" 2>/dev/null; do
  sleep 1
done
echo "scan_planner_node exited" >&2
wait "$scan_pid"
exit 1
"""


def assert_planner_only(script):
    lowered = script.lower()
    if "scan_planner_node" not in script:
        raise RuntimeError("SCAN helper must start scan_planner_node")
    if "cloud:=/quad_0/cloud" not in script:
        raise RuntimeError("SCAN helper must remap cloud:=/quad_0/cloud")
    if "robot_state_publisher" not in script:
        raise RuntimeError("SCAN helper must start robot_state_publisher")
    if "rviz_replay_node" not in script:
        raise RuntimeError("SCAN helper must start live rviz_replay_node")
    for token in FORBIDDEN_HELPER_TOKENS:
        if token in lowered:
            raise RuntimeError("SCAN helper must not start " + token)
    return script


class ScanOccupancy:
    def __init__(self, run_root, foxy_image_id, ros_domain_id, scan_workspace):
        self.root = Path(run_root)
        self.output = self.root / "artifacts/scan_occupancy"
        self.output.mkdir(parents=True, exist_ok=True)
        self.logs = self.root / "artifacts/logs"
        self.logs.mkdir(parents=True, exist_ok=True)
        self.foxy_image_id = foxy_image_id
        self.ros_domain_id = int(ros_domain_id)
        self.scan_workspace = Path(scan_workspace)
        self.name = "vla-p2b-stand-scan-" + self.root.name.lower().replace("_", "-")
        self.proc = None
        self.log_handle = None
        self.records = {
            "container": self.name,
            "scan_workspace": str(self.scan_workspace),
            "foxy_image_id": self.foxy_image_id,
            "ros_domain_id": self.ros_domain_id,
            "planner_only": True,
        }

    def command(self):
        script = assert_planner_only(helper_inner_script())
        return [
            "podman", "run", "--rm", "--pull=never", "--network=host", "--ipc=host",
            "--name", self.name,
            "-e", "ROS_DOMAIN_ID=%d" % self.ros_domain_id,
            "-e", "ROS_LOCALHOST_ONLY=1",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-v", str(self.root / "bridge") + ":/bridge:ro",
            "-v", str(self.root / "config") + ":/config:ro",
            "-v", str(self.root / "inputs/sensor_rig") + ":/robot:ro",
            "-v", str(self.logs) + ":/logs:rw",
            "-v", str(self.scan_workspace) + ":/workspace:ro",
            self.foxy_image_id,
            "bash", "-lc", script,
        ]

    def start(self):
        if not self.scan_workspace.is_dir():
            raise RuntimeError("scan_04 workspace missing: " + str(self.scan_workspace))
        urdf = self.root / "inputs/sensor_rig/lite3_pro_sensor_rig_real_with_interface.urdf"
        if not urdf.is_file():
            raise RuntimeError("canonical sensor-rig URDF missing: " + str(urdf))
        rewrite_urdf_meshes(urdf.read_text(encoding="utf-8"), urdf)
        planner = self.root / "config/planner.yaml"
        if not planner.is_file():
            raise RuntimeError("planner.yaml missing from package: " + str(planner))
        exists = subprocess.run(["podman", "container", "exists", self.name])
        if exists.returncode == 0:
            raise RuntimeError("refusing to reuse existing container: " + self.name)
        command = self.command()
        (self.output / "helper_command.json").write_text(
            json.dumps(command, indent=2, sort_keys=True) + "\n"
        )
        self.log_handle = (self.logs / "scan_occupancy_container.log").open("w", encoding="utf-8")
        self.proc = subprocess.Popen(
            command, stdout=self.log_handle, stderr=subprocess.STDOUT, start_new_session=True
        )
        self.records["started"] = True
        return self.records

    def exited_early(self):
        return self.proc is not None and self.proc.poll() is not None

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            subprocess.run(
                ["podman", "rm", "-f", self.name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                self.proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.log_handle is not None:
            self.log_handle.close()
            self.log_handle = None
        self.records["exit_code"] = None if self.proc is None else self.proc.returncode
        (self.output / "session.json").write_text(
            json.dumps(self.records, indent=2, sort_keys=True) + "\n"
        )
        return self.records
