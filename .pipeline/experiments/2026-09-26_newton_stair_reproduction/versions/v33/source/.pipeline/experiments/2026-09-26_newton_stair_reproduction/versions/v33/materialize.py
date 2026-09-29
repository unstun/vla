"""Apply v33's change after verifying the frozen parent v32 (versions/v33/PLAN.md).

In the simulator, the backend judges body-pose freshness by simulation time: the pose's simulation-time age
against /clock must stay within odom_stale_s (0.25 s), and its wall-time age within a 2.0 s backstop for a
stopped simulator or a stalled pose path (/clock travels with the poses). The wall base stays the default
everywhere else. Five files change. The four source files are edited on the bytes (all are LF-only ASCII) at
anchors that occur exactly once, verified to reverse to the v32 bytes. setup/runtime_sources.json, the import
record that run_local_episode.py re-hashes before physics, then gets the three runtime files' new sha256 and
bytes, their import hash kept as archived_sha256 and a local_modification note, as v11, v14 and v26 did.
Decisions: Dr Sun, 2026-09-29 (simulation-time gate first, simulator only; 2.0 s wall backstop; after review
round 1, the 2.0 s backstop kept for a stalled pose path too, with the case documented and flagged in analysis).
"""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
CONTRACTS = BASE / "runtime_sources/backend_adapter/backend_adapter/contracts.py"
GATE = BASE / "runtime_sources/backend_adapter/backend_adapter/control_gate.py"
NODE = BASE / "runtime_sources/backend_ros/p2b_backend_ros/node.py"
GRAPH = BASE / "scripts/native_graph.py"
RECORD = BASE / "setup/runtime_sources.json"
# The import record's note for each changed runtime file (node.py keeps its v11 and v14 history).
NOTES = {
    CONTRACTS: "v33 simulation-time body-pose freshness (GateConfig.odom_time_base and odom_wall_backstop_s, "
               "MeasuredState.stamp_s); preimage and patch in versions/v33",
    GATE: "v33 simulation-time body-pose freshness (CommandGate.sim_clock and measurement_stale); "
          "preimage and patch in versions/v33",
    NODE: "v11 fault propagation; v14 consumer-scoped replies; v33 /clock subscription and simulation-time "
          "body-pose freshness; preimages and patches in versions/v11, versions/v14 and versions/v33",
}

# (file, anchor, text, where): "after" inserts text after the anchor, "before" before it, "replace" replaces it.
EDITS = [
    (CONTRACTS, b'    source: str = "diagnostic_sim_truth"\n',
     b"    # v33: the pose's header stamp in simulation seconds, when the source provides one.\n"
     b"    stamp_s: Optional[float] = None\n", "after"),
    (CONTRACTS, b'        require_identifier("source", self.source)\n',
     b"        if self.stamp_s is not None:\n"
     b'            require_finite("stamp_s", self.stamp_s)\n', "after"),
    (CONTRACTS, b"    still_window_s: float = 0.50\n",
     b'    # v33: "simulation" judges body-pose freshness by its simulation-time age against /clock, plus a\n'
     b'    # wall-time backstop for a stopped simulator or a stalled pose path; "wall" keeps the wall time between\n'
     b'    # receipts.\n'
     b'    odom_time_base: str = "wall"\n'
     b"    odom_wall_backstop_s: float = 2.0\n", "after"),
    (CONTRACTS, b'        require_nonnegative("still_window_s", self.still_window_s)\n',
     b'        if self.odom_time_base not in ("wall", "simulation"):\n'
     b'            raise ContractError("invalid_odom_time_base")\n'
     b'        require_nonnegative("odom_wall_backstop_s", self.odom_wall_backstop_s)\n'
     b'        if self.odom_time_base == "simulation" and self.odom_wall_backstop_s < self.odom_stale_s:\n'
     b'            raise ContractError("invalid_odom_wall_backstop_s")\n', "after"),
    (GATE, b"    def __init__(self, config: Optional[GateConfig] = None, clock: Callable[[], float] = time.monotonic) -> None:\n",
     b"    def __init__(\n"
     b"        self,\n"
     b"        config: Optional[GateConfig] = None,\n"
     b"        clock: Callable[[], float] = time.monotonic,\n"
     b"        sim_clock: Optional[Callable[[], Optional[float]]] = None,\n"
     b"    ) -> None:\n", "replace"),
    (GATE, b"        self.events = []  # type: List[Dict[str, Any]]\n",
     b"        self.sim_clock = sim_clock  # v33: newest /clock in seconds, or None before the first\n", "after"),
    (GATE, b"        if self.last_measurement is None or now - self.last_measurement.monotonic_s > self.config.odom_stale_s:\n",
     b"        if self.measurement_stale(self.last_measurement, now):\n", "replace"),
    (GATE, b"    def snapshot(self) -> Dict[str, Any]:\n",
     b"    def measurement_stale(self, measurement: Optional[MeasuredState], now: float) -> bool:\n"
     b'        """Whether a body pose is too old to steer by.\n'
     b"\n"
     b"        Wall base: its wall-time age exceeds odom_stale_s. Simulation base (v33): its simulation-time age\n"
     b"        against the newest /clock exceeds odom_stale_s, or its wall-time age exceeds odom_wall_backstop_s\n"
     b"        (/clock stops with a stopped simulator and with a stalled pose path, as it travels with the poses);\n"
     b"        a missing stamp or clock counts as stale.\n"
     b'        """\n'
     b"        if measurement is None:\n"
     b"            return True\n"
     b'        if self.config.odom_time_base == "wall":\n'
     b"            return now - measurement.monotonic_s > self.config.odom_stale_s\n"
     b"        sim_now = self.sim_clock() if self.sim_clock is not None else None\n"
     b"        if measurement.stamp_s is None or sim_now is None:\n"
     b"            return True\n"
     b"        return (max(0.0, sim_now - measurement.stamp_s) > self.config.odom_stale_s\n"
     b"                or now - measurement.monotonic_s > self.config.odom_wall_backstop_s)\n"
     b"\n", "before"),
    (NODE, b"        self.watchdog_timer = node.create_timer(0.02, self._watchdog_tick)\n",
     b"        # v33: in the simulator, body-pose freshness is judged against /clock. The bridge publishes /clock from\n"
     b"        # the state sample of each pose (reliable, depth 1); node timers keep wall time.\n"
     b"        self._sim_clock_ns = None  # type: Optional[int]\n"
     b"        self._sim_clock_backward = 0\n"
     b'        if gate.config.odom_time_base == "simulation":\n'
     b"            from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy\n"
     b"            from rosgraph_msgs.msg import Clock\n"
     b"            clock_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,\n"
     b"                                   durability=DurabilityPolicy.VOLATILE, history=HistoryPolicy.KEEP_LAST)\n"
     b'            self.clock_sub = node.create_subscription(Clock, topics.get("clock_topic", "/clock"), self._on_sim_clock, clock_qos)\n'
     b"            gate.sim_clock = self.sim_now\n", "after"),
    (NODE, b'            raise RuntimeError("body_pose_not_ready")\n',
     b'        if self.gate.config.odom_time_base == "simulation":\n'
     b"            if self.gate.measurement_stale(self._last_measurement, time.monotonic()):\n"
     b'                raise RuntimeError("body_pose_stale")\n'
     b"            return self._last_measurement\n", "after"),
    (NODE, b"    def pct_start_provider(self) -> MeasuredState:\n",
     b"    def sim_now(self) -> Optional[float]:\n"
     b"        clock_ns = self._sim_clock_ns\n"
     b"        return None if clock_ns is None else clock_ns / 1e9\n"
     b"\n"
     b"    def _on_sim_clock(self, msg: Any) -> None:\n"
     b"        clock_ns = int(msg.clock.sec) * 1000000000 + int(msg.clock.nanosec)\n"
     b"        if self._sim_clock_ns is not None and clock_ns < self._sim_clock_ns:\n"
     b"            self._sim_clock_backward += 1\n"
     b"            return\n"
     b"        self._sim_clock_ns = clock_ns\n"
     b"\n", "before"),
    (NODE, b'            "last_body_pose_age_s": None if self._last_measurement is None else time.monotonic() - self._last_measurement.monotonic_s,\n',
     b'            "odom_time_base": self.gate.config.odom_time_base,\n'
     b'            "sim_clock_s": self.sim_now(),\n'
     b'            "sim_clock_backward_events": self._sim_clock_backward,\n'
     b'            "last_body_pose_sim_age_s": (None if self._last_measurement is None or self._last_measurement.stamp_s is None\n'
     b"                                         or self.sim_now() is None else self.sim_now() - self._last_measurement.stamp_s),\n",
     "after"),
    (NODE, b'                source="diagnostic_sim_truth_body_pose",\n',
     b"                stamp_s=self._last_odom_stamp_ns / 1e9,\n", "after"),
    (GRAPH, b'        backend["service"]["command_timeout_s"] = request.get("goal_wall_budget_s", 35.0)\n',
     b"        # v33: in this simulator the backend judges body-pose freshness by simulation time, with a 2.0 s wall-time\n"
     b"        # backstop for a stopped simulator or a stalled pose path (Dr Sun, 2026-09-29). Every other gate keeps\n"
     b"        # wall time.\n"
     b'        backend["gate"].update(odom_time_base="simulation", odom_wall_backstop_s=2.0)\n', "after"),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def apply(data, anchor, text, where):
    return data.replace(anchor, {"after": anchor + text, "before": text + anchor, "replace": text}[where])


def update_record(record_bytes, sources):
    """The import record with the changed runtime files' new sha256 and bytes (v11/v14/v26 precedent).

    `sources` maps each runtime file in NOTES to its new bytes. A first modification keeps the import hash as
    archived_sha256; an existing archived_sha256 (node.py's, from before v11) is kept. The file is rewritten in
    its own format, json.dumps(indent=2) plus a newline.
    """
    data = json.loads(record_bytes)
    for path, note in NOTES.items():
        row = next(r for r in data["records"] if r["path"] == str(path.relative_to(BASE)))
        row.setdefault("archived_sha256", row["sha256"])
        row.update(sha256=sha(sources[path]), bytes=len(sources[path]), local_modification=note)
    return (json.dumps(data, indent=2) + "\n").encode()


def main():
    assert not (HERE / "prepared.json").exists()
    parent = json.loads((HERE.parent / "v32/manifest.json").read_text())
    for name, digest in parent["source_files"].items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    sources = [CONTRACTS, GATE, NODE, GRAPH]
    files = sources + [RECORD]
    before = {path: path.read_bytes() for path in files}
    # node.py, native_graph.py and the import record are in v32's manifest, checked above. contracts.py and
    # control_gate.py are not; the v32-checked record pins them. Every record must match, as run_local_episode.py
    # requires before physics.
    records = json.loads(before[RECORD])["records"]
    assert all(sha((BASE / r["path"]).read_bytes()) == r["sha256"] for r in records)
    assert before[RECORD] == (json.dumps(json.loads(before[RECORD]), indent=2) + "\n").encode()
    after = dict(before)
    for path, anchor, text, where in EDITS:
        assert b"\r" not in before[path]
        assert after[path].count(anchor) == 1, (path.name, anchor)
        after[path] = apply(after[path], anchor, text, where)
    after[RECORD] = update_record(before[RECORD], after)
    # Byte-exact record: undoing every edit, last first, gives the parent bytes back.
    for path in sources:
        restored = after[path]
        for p, anchor, text, where in reversed(EDITS):
            if p != path:
                continue
            new = {"after": anchor + text, "before": text + anchor, "replace": text}[where]
            assert restored.count(new) == 1, (path.name, anchor)
            restored = restored.replace(new, anchor)
        assert restored == before[path], path
    # The record: putting the three preimage rows back gives the parent bytes back.
    old_rows = {r["path"]: r for r in json.loads(before[RECORD])["records"]}
    undone = json.loads(after[RECORD])
    undone["records"] = [old_rows[r["path"]] for r in undone["records"]]
    assert (json.dumps(undone, indent=2) + "\n").encode() == before[RECORD]
    patch = []
    for path in files:
        preimage = HERE / "parent_source" / path.relative_to(BASE)
        preimage.parent.mkdir(parents=True, exist_ok=True)
        preimage.write_bytes(before[path])
        path.write_bytes(after[path])
        relative = str(path.relative_to(BASE))
        patch += difflib.unified_diff(before[path].decode().splitlines(True), after[path].decode().splitlines(True),
                                      fromfile="v32/" + relative, tofile="v33/" + relative)
    (HERE / "changes.patch").write_text("".join(patch))
    for name in ("building_planner.yaml", "flat_planner.yaml"):
        shutil.copyfile(HERE.parent / "v32" / name, HERE / name)
    prepared = json.loads((HERE.parent / "v32/prepared.json").read_text())
    (HERE / "prepared.json").write_text(json.dumps({
        "parent": "v32", "status": "unfrozen_candidate", "native_build": prepared["native_build"],
        "changed_files": [str(path.relative_to(ROOT)) for path in files],
        "before_sha256": {str(path.relative_to(ROOT)): sha(before[path]) for path in files},
        "after_sha256": {str(path.relative_to(ROOT)): sha(after[path]) for path in files},
        "edits": len(EDITS),
        "record_updates": sorted(str(path.relative_to(BASE)) for path in NOTES),
        "basis": ".pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v33/evidence/pose_gap_survey.json",
    }, indent=2) + "\n")
    print(json.dumps({str(path.relative_to(BASE)): after[path].count(b"\n") - before[path].count(b"\n") for path in files}))


if __name__ == "__main__":
    main()
