#!/usr/bin/env python3
"""Prepare/execute one bounded RTX/PCT/SCAN stair observation with local video."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shlex
import shutil
import yaml

from height_reference_contract import (SPAWN_BODY_HEIGHT_M, LOCOMOTION_REFERENCE_HEIGHT_M,
                                       PINNED_SOURCES, validate_declared_heights)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OLD = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln"
SCENARIO = HERE / "prepared/stair_video_scenario_v1"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


two = module("stair_two_goal_reference", OLD / "isaac_runner/run_two_goal_pilot.py")
qualify = module("stair_livox_assets", OLD / "isaac_runner/qualify_stand_runner.py")
materializer = module("stair_rtx_materializer", HERE / "materialize_rtx_runner.py")


def write(path, value):
    """Atomic replacement also breaks a package's inherited input hardlink."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".new")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def planner_with_clearance(text, clearance):
    result = two._insert_ros_parameter(text, "grid_map.reactive_body_clearance: " + str(clearance))
    values = yaml.safe_load(result)["scan_planner_node"]["ros__parameters"]
    if values["grid_map.body_height"] != 0.0 or values["grid_map.reactive_body_clearance"] != clearance:
        raise ValueError("route offset and physical body clearance must remain separate")
    return result


def worker_source(static_background_tracker=False, locomotion_height_contract=False):
    source = two.remote_worker_source()
    source = materializer.once(source,
        '    gpu_sampler = GpuSampler(artifacts / "gpu_samples.jsonl", GPU_SAMPLE_INTERVAL_S)\n',
        '    idle = subprocess.run(["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10)\n'
        '    if idle.returncode or idle.stdout.strip():\n'
        '        raise RuntimeError("GPU must be idle before the bounded stair run")\n'
        '    gpu_sampler = GpuSampler(artifacts / "gpu_samples.jsonl", GPU_SAMPLE_INTERVAL_S)\n')
    source = source.replace('known-map truth-pose diagnostic two-goal pilot; no LLM/Cortex/SLAM/physical robot',
                            'bounded stair observation with actual RTX geometric sweeps and official human; no LLM/Cortex/SLAM/physical robot')
    start = source.index('        pct_cmd = [\n')
    end = source.index('        write_json(artifacts / "pct_worker_command.json", pct_cmd)', start)
    pct = '''        pct_script = """set -eo pipefail
source /opt/ros/humble/setup.bash
export PYTHONPATH=/qualification/backend_adapter:/qualification/pct_runtime/python:/qualification/bridge/lite3_sim_bridge:${{PYTHONPATH:-}}
export LD_LIBRARY_PATH=/qualification/pct_runtime/lib:${{LD_LIBRARY_PATH:-}}
python3 /qualification/bridge/lite3_sim_bridge/pct_sim_clock_publisher.py --ros-args -p map_path:=/qualification/inputs/new_building.pickle -p use_sim_time:=true >/logs/pct_support.log 2>&1 &
support_pid=$!
python3 -m backend_adapter.pct_worker --host 127.0.0.1 --port {port} --pct-source-root /qualification/pct_runtime/python --rsg-root /qualification/inputs --tomogram-path /qualification/inputs/new_building.pickle --reference-height-m 0.35 &
worker_pid=$!
trap 'kill "$support_pid" "$worker_pid" 2>/dev/null || true' EXIT INT TERM
wait -n "$support_pid" "$worker_pid"
exit 1
""".format(port=args.pct_port)
        pct_cmd = ["podman", "run", "--rm", "--pull=never", "--network=host", "--ipc=host", "--name", pct_container,
                   "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "ROS_LOCALHOST_ONLY=1",
                   "-e", "ROS_DOMAIN_ID=%d" % args.ros_domain_id,
                   "-v", str(run_root) + ":/qualification:ro", "-v", str(logs) + ":/logs:rw",
                   args.pct_image_id, "bash", "-lc", pct_script]
'''
    source = source[:start] + pct + source[end:]
    source = materializer.once(source, 'controller_pid=$!\ncleanup() {{\n',
        'controller_pid=$!\n'
        'ros2 run scan_reactive_tracker moving_cluster_tracker --ros-args -p use_sim_time:=true > /logs/moving_cluster_tracker.log 2>&1 &\n'
        'tracker_pid=$!\n'
        'python3 -m lite3_sim_bridge.reactive_health --output {health_path} --run-id {run_id} --epoch {run_epoch_ns} --ros-args -p use_sim_time:=true > /logs/reactive_health.log 2>&1 &\n'
        'health_pid=$!\n'
        'cleanup() {{\n')
    source = materializer.once(source, '  kill "$scan_pid" "$controller_pid" 2>/dev/null || true\n',
                               '  kill "$scan_pid" "$controller_pid" "$tracker_pid" "$health_pid" "$backend_pid" 2>/dev/null || true\n')
    backend_line = next(line for line in source.splitlines()
                        if line.startswith("python3 -m p2b_backend_ros.node --config"))
    source = materializer.once(source, backend_line + "\n",
                               backend_line + ' &\nbackend_pid=$!\n'
                               'wait -n "$scan_pid" "$controller_pid" "$tracker_pid" "$health_pid" "$backend_pid"\nexit 1\n')
    source = materializer.once(source, '            ros_domain_id=args.ros_domain_id,\n',
                               '            ros_domain_id=args.ros_domain_id,\n'
                               '            health_path=shlex.quote(str(artifacts / "runtime_health.json")),\n')
    before = '''        driver = subprocess.run(driver_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=1200)
        (logs / "pilot_driver.log").write_text(driver.stdout, encoding="utf-8")
        result["pilot_driver_exit_code"] = driver.returncode
        if driver.returncode != 0:
            raise RuntimeError("pilot driver failed with exit %d" % driver.returncode)
'''
    after = '''        driver = start_popen(driver_cmd, logs / "pilot_driver.log")
        processes.append(("driver", driver))
        deadline = time.monotonic() + 900.0
        while driver.poll() is None:
            dead = [(name, proc.returncode) for name, proc in processes if name != "driver" and proc.poll() is not None]
            if dead:
                raise RuntimeError("required runtime process exited: " + repr(dead))
            if time.monotonic() > deadline:
                raise RuntimeError("stair driver wall deadline exceeded")
            time.sleep(0.1)
        result["pilot_driver_exit_code"] = driver.returncode
        if driver.returncode != 0:
            raise RuntimeError("stair driver failed with exit %d" % driver.returncode)
'''
    source = materializer.once(source, before, after)
    if static_background_tracker:
        source = materializer.once(source,
            '            "-v", str(scan_ws) + ":/workspace:ro",\n',
            '            "-v", str(scan_ws) + ":/workspace:ro",\n'
            '            "-v", str(run_root) + ":/qualification:ro",\n')
        source = materializer.once(source, 'support_pid=$!\n',
            'support_pid=$!\n'
            'python3 /qualification/bridge/lite3_sim_bridge/pct_sim_clock_publisher.py --ros-args -r __node:=pct_tracking_ground_publisher -p map_path:=/qualification/inputs/new_building.pickle -p ground_mode:=tracking_physical -p use_sim_time:=true >/logs/tracker_ground.log 2>&1 &\n'
            'tracking_ground_pid=$!\n')
        source = materializer.once(source, 'kill "$support_pid" "$worker_pid"',
                                   'kill "$support_pid" "$worker_pid" "$tracking_ground_pid"')
        source = materializer.once(source, 'wait -n "$support_pid" "$worker_pid"',
                                   'wait -n "$support_pid" "$worker_pid" "$tracking_ground_pid"')
        source = materializer.once(source,
            'ros2 run scan_reactive_tracker moving_cluster_tracker --ros-args -p use_sim_time:=true',
            'python3 /qualification/inputs/static_background/unpack_foreground_dependency.py --wheel /qualification/inputs/static_background/scipy.whl --manifest /qualification/inputs/static_background/dependency_manifest.json --destination /tmp/foreground_dependencies --receipt /logs/foreground_dependency_receipt.json\n'
            'env OPENBLAS_NUM_THREADS=1 PYTHONPATH=/tmp/foreground_dependencies:${{PYTHONPATH:-}} ros2 run scan_reactive_tracker moving_cluster_tracker --ros-args -p use_sim_time:=true -p static_background_pcd:=/qualification/inputs/static_background/building2_9.pcd')
    if locomotion_height_contract:
        source = materializer.once(source, "--reference-height-m 0.35 &", "--reference-height-m 0.30 &")
    compile(source, "remote_worker.py", "exec")
    return source


def stage_foreground_inputs(local, build):
    """Stage only the verified VLA-owned prior/dependency for an explicit V3 run."""
    repair = HERE / "repairs/2026-09-26_sequential/step2_tracking"
    acceptance = json.loads((repair / "foxy_scan22_v1/review.json").read_text())
    if acceptance.get("passed") is not True:
        raise ValueError("recorded-input ROS tracker gate is incomplete")
    expected = json.loads((repair / "foxy_scan22_v1/results/numeric/result.json").read_text())["source_sha256"]
    module_root = build / "src/scan_reactive_tracker/scan_reactive_tracker"
    if any(two.sha256(module_root / name) != digest for name, digest in expected.items()):
        raise ValueError("tracker differs from the runtime-verified V3 source")
    asset_root = local / "inputs/static_background"
    asset_root.mkdir()
    asset = ROOT / "references/upstream/2026-09-26_pct_building_static_background/source/building2_9.pcd"
    if two.sha256(asset) != "8721efeb74415336d47c97d861d6e30ad213669b120d5b37c62461100c1f2eae":
        raise ValueError("Building prior identity changed")
    deps = repair / "dependencies/scipy_1_8_1_cp38"
    metadata = json.loads((deps / "manifest.json").read_text())
    wheel = deps / metadata["filename"]
    if two.sha256(wheel) != "23b22fbeef3807966ea42d8163322366dd89da9bebdc075da7034cee3a1441ca":
        raise ValueError("verified Foxy dependency changed")
    for source, name in ((asset, "building2_9.pcd"), (wheel, "scipy.whl"),
                         (deps / "manifest.json", "dependency_manifest.json"),
                         (repair / "unpack_foreground_dependency.py", "unpack_foreground_dependency.py")):
        shutil.copy2(source, asset_root / name)
    write(asset_root / "identity.json", {
        "files": {p.name: two.sha256(p) for p in asset_root.iterdir()},
        "tracker_source_sha256": expected,
        "recorded_ros_gate_sha256": two.sha256(repair / "foxy_scan22_v1/review.json"),
        "claim": "Tracker-only prior. Raw obstacle clouds, selected navigation ground, and occupancy thresholds remain unchanged."})
    (asset_root / ".gitignore").write_text("# Local staging copies; identity.json pins source and bytes.\n/building2_9.pcd\n/scipy.whl\n")


def prepare(args):
    gate = json.loads(args.sensor_gate.read_text())
    if gate.get("stage") != "mid360" or gate.get("passed") is not True:
        raise ValueError("actual MID-360 geometric/tracker sensor gate has not passed")
    local, commands = two.prepare(args)
    remote = commands["remote_run"]
    scenario_dir = args.scenario_dir
    scenario = json.loads((scenario_dir / "scenario.json").read_text())
    scenario["mode"] = args.mode
    reference_height = None
    if args.locomotion_height_contract:
        evidence_path = HERE / "repairs/2026-09-26_sequential/step6_body_reference/height_contract_evidence.json"
        evidence = json.loads(evidence_path.read_text())
        if evidence.get("source_hashes_match") is not True or evidence["source_sha256"] != PINNED_SOURCES:
            raise ValueError("V12 height source evidence changed or is incomplete")
        validate_declared_heights(evidence["declared_spawn_height_m"], evidence["configured_locomotion_height_target_m"])
        reference_height = LOCOMOTION_REFERENCE_HEIGHT_M
        shutil.copy2(evidence_path, local / "inputs/locomotion_height_contract.json")
        scenario.update(spawn_body_height_m=SPAWN_BODY_HEIGHT_M, locomotion_reference_height_m=reference_height)
    if args.static_background_tracker:
        if args.reference_run is not None:
            raise ValueError("a placement-only ablation cannot also change the tracker")
        stage_foreground_inputs(local, Path(args.accepted_scan_build_dir))
        scenario["track_source_id"] = "sensor_lidar_static_background_cluster_v3"
    write(local / "inputs/stair_scenario.json", scenario)
    shutil.copy2(scenario_dir / "actor_route.json", local / "inputs/actor_route.json")
    shutil.copy2(scenario_dir / "geometry.json", local / "inputs/stair_geometry.json")
    shutil.copy2(args.sensor_gate, local / "inputs/rtx_sensor_gate.json")
    candidate = local / "rtx_candidate"
    materializer.materialize(candidate, local / "inputs/actor_route.json", args.locomotion_height_contract)
    bridge = local / "bridge/lite3_sim_bridge"
    for source in candidate.glob("*.py"):
        shutil.copy2(source, bridge / source.name)
    for name in ("pct_sim_clock_core.py", "pct_sim_clock_publisher.py"):
        shutil.copy2(OLD / "p2b_execution/reactive_stair" / name, bridge / name)
    shutil.copy2(HERE / "reactive_health.py", bridge / "reactive_health.py")
    qualify.stage_livox_assets(local)
    asset = local / "inputs/official_human"
    asset.mkdir()
    original = ROOT / "references/upstream/2026-09-24_isaac_official_police_human"
    shutil.copy2(original / "male_adult_police_04.usd", asset / "male_adult_police_04.usd")
    shutil.copytree(original / "textures", asset / "textures")
    cache = asset / "cache"
    cache.mkdir()
    for name in ("official_human_retarget_cache.npz", "official_human_retarget_cache.json"):
        shutil.copy2(HERE.parent / "official_human_cache" / name, cache / name)
    pilot = json.loads((local / "inputs/pilot.json").read_text())
    pilot.update({"spawn_ground_xyz_m": scenario["spawn_ground_xyz_m"], "spawn_yaw_rad": scenario["spawn_yaw_rad"],
                  "max_sim_seconds": scenario["max_sim_seconds"], "max_wall_seconds": scenario["max_wall_seconds"],
                  "goals": [{"goal_id": "metadata-midpoint", "ground_xyz_m": [-5.3, 2.0, 0.740234375]},
                            {"goal_id": "stair-goal", "ground_xyz_m": scenario["goal_ground_xyz_m"]}],
                  "selection": "Separately screened stair endpoints; PCT computes the runtime route",
                  "required_arrivals": 0, "cancellation_test": "end-of-observation cancellation is not avoidance"})
    if args.locomotion_height_contract:
        if pilot["nominal_body_height_m"] != SPAWN_BODY_HEIGHT_M:
            raise ValueError("legacy pilot spawn height changed")
        pilot.update(spawn_body_height_m=SPAWN_BODY_HEIGHT_M, locomotion_reference_height_m=reference_height)
    write(local / "inputs/pilot.json", pilot)
    planner = local / "config/planner.yaml"
    planner.write_text(planner_with_clearance(planner.read_text(), reference_height if reference_height is not None else pilot["nominal_body_height_m"]))
    if args.known_lite3_trunk:
        robot_urdf = local / qualify.ISAAC_URDF_PACKAGE_REL
        if two.sha256(robot_urdf) != "803d552703bcc4f72ce15f38b95bc3f62e3e4ada0b42bf3ecf71b32b6590bb9d":
            raise ValueError("known trunk geometry requires the exact pinned robot URDF")
        planner.write_text(two._insert_ros_parameter(planner.read_text(), "grid_map.reactive_known_lite3_trunk: true"))
        yaml.safe_load(planner.read_text())
    write(local / "inputs/two_goal_route_artifact.json", two.make_route_artifact(pilot))
    two.make_backend_config(local / "config/p2b_backend_ros.two_goal.json", pilot, local.name, args.http_port, args.pct_port)
    config = json.loads((local / "config/p2b_backend_ros.two_goal.json").read_text())
    config["map"]["epoch"] = "stair_reactive"
    if args.locomotion_height_contract:
        config["map"]["nominal_body_height_m"] = reference_height
    write(local / "config/p2b_backend_ros.two_goal.json", config)
    argv = two.build_runner_argv(args, remote, local.name, pilot)
    argv += ["--lidar-pattern-mode", "livox_mid360", "--lidar-pattern-csv", remote + "/" + qualify.MID360_CSV_PACKAGE_REL,
             "--robot-asset", remote + "/" + qualify.ISAAC_URDF_PACKAGE_REL,
             "--canonical-robot-asset", remote + "/" + qualify.CANONICAL_URDF_PACKAGE_REL,
             "--lidar-max-range", "40.0", "--official-human-asset-root", remote + "/inputs/official_human",
             "--official-human-cache-dir", remote + "/inputs/official_human/cache",
             "--official-human-route", remote + "/inputs/actor_route.json"]
    for key, value in scenario["camera"].items():
        argv += ["--camera-" + key.replace("_", "-"), str(value)]
    manifest = two.bridge_manifest(local / "bridge", remote + "/bridge")
    write(local / "inputs/execution_manifest.json", manifest)
    runner = bridge / "run_pct_scan_building.py"
    runner_module = two.import_runner(runner)
    baseline = json.loads((OLD / "p2b_execution/baseline_config/native_nominal_scope.json").read_text())
    scope = two.make_scope(runner_module, argv, two.sha256(local / "inputs/execution_manifest.json"), two.sha256(runner), pilot, baseline)
    scope["claim"] = "Bounded stair scene with official animated human and measured RTX/Livox geometric sweeps; no VLA or real robot"
    if args.locomotion_height_contract:
        scope["platform_segment"].update(spawn_body_height_m=SPAWN_BODY_HEIGHT_M,
                                         locomotion_reference_height_m=reference_height)
        scope["height_reference_contract_sha256"] = two.sha256(local / "inputs/locomotion_height_contract.json")
    scope["tcp_ports"] = {"telemetry": args.telemetry_port, "command": args.command_port, "http": args.http_port, "pct": args.pct_port}
    write(local / "inputs/two_goal_scope.json", scope)
    driver = two.pilot_driver_source().split("def main():", 1)[0] + (HERE / "stair_driver_body.py").read_text()
    compile(driver, "pilot_driver.py", "exec")
    (local / "pilot_driver.py").write_text(driver)
    (local / "remote_worker.py").write_text(worker_source(args.static_background_tracker, args.locomotion_height_contract))
    parts = shlex.split(commands["run"][-1])
    parts[parts.index("--runner-argv-json") + 1] = json.dumps(argv, separators=(",", ":"))
    commands["run"][-1] = shlex.join(parts)
    write(local / "commands.json", commands)
    if args.reference_run is not None:
        reference = args.reference_run
        previous = json.loads((reference / "commands.json").read_text())
        old_parts = shlex.split(previous["run"][-1])
        old_argv = json.loads(old_parts[old_parts.index("--runner-argv-json") + 1])
        expected_argv = [v.replace(previous["remote_run"], remote) for v in old_argv]
        run_id_index = expected_argv.index("--external-run-id") + 1
        if expected_argv[run_id_index] != reference.name:
            raise ValueError("reference runner identity does not match its run directory")
        expected_argv[run_id_index] = local.name
        if argv != expected_argv:
            raise ValueError("placement ablation changed the original Isaac arguments")
        preserved = ["config/planner.yaml", "config/controller.yaml", "inputs/pilot.json", "remote_worker.py"]
        for name in preserved:
            if two.sha256(local / name) != two.sha256(reference / name):
                raise ValueError("placement ablation changed reference file: " + name)
        old_route_sha = two.sha256(reference / "inputs/actor_route.json")
        new_route_sha = two.sha256(local / "inputs/actor_route.json")
        for path in bridge.rglob("*.py"):
            old_path = reference / path.relative_to(local)
            expected = old_path.read_text()
            if path.name == "official_building_human.py":
                expected = materializer.once(expected, old_route_sha, new_route_sha)
            if path.read_text() != expected:
                raise ValueError("placement ablation changed bridge behavior: " + path.name)
        # Preserve the reference trial's goal timing as well as its sensor and
        # planner configuration. The newer settled-start driver is not mixed in.
        shutil.copy2(reference / "pilot_driver.py", local / "pilot_driver.py")
        write(local / "placement_comparison.json", {
            "reference_run": str(reference), "reference_return_verdict_sha256": two.sha256(reference / "return_verdict.json"),
            "preserved_sha256": {name: two.sha256(local / name) for name in preserved + ["pilot_driver.py"]},
            "runner_arguments_match_after_run_path_and_id_replacement": True,
            "bridge_behavior_match_except_actor_route_hash": True,
            "changed_factor": "official actor lateral position and its geometry/provenance records"})
    identity = json.loads((local / "source_env_hashes.json").read_text())
    identity["base_pilot_sha256"] = identity["pilot_sha256"]
    identity["pilot_sha256"] = two.sha256(local / "inputs/pilot.json")
    identity["patched_runner_sha256"] = two.sha256(runner)
    identity["execution_manifest_sha256"] = two.sha256(local / "inputs/execution_manifest.json")
    write(local / "source_env_hashes.json", identity)
    (local / "inputs/package_manifest.json").unlink()
    write(local / "inputs/package_manifest.json", two.package_manifest(local))
    return local, commands


def main():
    parser = two.build_parser()
    parser.set_defaults(local_runs_root=HERE / "runs", remote_root="/home/sun/vla_exec/2026-09-26_stair_video",
                        accepted_scan_build_dir=str(OLD / "p2b_execution/builds/scan_11"),
                        remote_scan_workspace="/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_11",
                        ros_domain_id=196, telemetry_port=46260, command_port=46261, http_port=8785, pct_port=47651)
    parser.add_argument("--mode", choices=("stand", "walk"), required=True)
    parser.add_argument("--scenario-dir", type=Path, default=SCENARIO)
    parser.add_argument("--known-lite3-trunk", action="store_true")
    parser.add_argument("--static-background-tracker", action="store_true")
    parser.add_argument("--locomotion-height-contract", action="store_true")
    parser.add_argument("--reference-run", type=Path)
    parser.add_argument("--sensor-gate", type=Path, default=HERE.parent / "rtx_sensing/runs/mid360_v5_release_order/execution_result.json")
    args = parser.parse_args()
    existing = Path(args.local_runs_root) / str(args.run_id)
    if args.execute and existing.is_dir():
        if (existing / "preparation_failure.json").exists():
            raise ValueError("refusing execution of an incomplete preparation package")
        local, commands = existing, json.loads((existing / "commands.json").read_text())
        if json.loads((existing / "inputs/stair_scenario.json").read_text())["mode"] != args.mode:
            raise ValueError("execution mode differs from the prepared scenario")
    else:
        local, commands = prepare(args)
    print("prepared", local, flush=True)
    if args.execute:
        two.execute(args, local, commands)


if __name__ == "__main__":
    main()
