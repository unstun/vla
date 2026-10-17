"""Own one local native-ROS container and one bounded Newton episode (v192 Option B)."""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

VERSION = Path(__file__).resolve().parent
BASE = VERSION.parents[1]
PROJECT = BASE.parents[2]
BUILD = VERSION
IMAGE = os.environ.get("V192_EXECUTION_IMAGE")


def verify_integration_version(out, version=None):
    versions = BASE / "versions"
    if version is None and (versions / "current.json").exists():
        version = json.loads((versions / "current.json").read_text())["current"]
    if version is None:
        return None
    if not (version.startswith("v") and version[1:].isdigit()):
        raise ValueError("Expected an integer integration version such as v4")
    manifest_path = versions / version / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for name, expected in manifest["source_files"].items():
        if hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Version source changed; register a new version before running: " + name)
    shutil.copyfile(manifest_path, out / "integration_version.json")
    return version


def verify_native_build(build, frozen):
    from native_gate import verify
    return verify(build, frozen)


HISTORICAL_PROFILE_SHA256 = "6afa0e573c268aca641f7d176f55bbf720b6521db8e5ce8153e2baece1b5b621"

def prepare_external_directory(out):
    external = out / "artifacts/external_episode"
    if external.exists() and (external.is_symlink() or not external.is_dir() or any(external.iterdir())):
        raise FileExistsError("Applied-state storage already contains data: " + str(external))
    external.mkdir(parents=True, exist_ok=True)


def building_scenario(profile, wall_budget):
    if profile == "corner_start":
        from corner_fixture import load_corner
        scenario = load_corner()
        scenario.update(max_sim_seconds=40., max_wall_seconds=wall_budget)
        return scenario
    if profile not in ("short_stair", "historical_full"):
        raise ValueError("Unknown Building route profile")
    historical = profile == "historical_full"
    path = BASE / "inputs" / ("historical_full_building.json" if historical else "stair_scenario.json")
    if historical and hashlib.sha256(path.read_bytes()).hexdigest() != HISTORICAL_PROFILE_SHA256:
        raise ValueError("Historical Building profile SHA-256 mismatch")
    scenario = json.loads(path.read_text())
    scenario.update(max_sim_seconds=600. if historical else 90., max_wall_seconds=wall_budget,
                    navigation_input="native PCT map, actual geometric LiDAR and simulator body localization",
                    scene_condition=("Complete archived Building; historical full-floor route; no added actor" if historical else
                                     "Complete archived Building; fixed architecture; no added actor"))
    return scenario


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--backend-executor", choices=("multi", "single"), default="multi")
    parser.add_argument("--applied-transport", choices=("shared",), default="shared")
    parser.add_argument("--native-build", type=Path, default=BUILD)
    parser.add_argument("--geometry-obstacles", action="store_true")
    parser.add_argument("--static-human", action="store_true")
    parser.add_argument("--planner-config", type=Path)
    parser.add_argument("--scene", choices=("building", "building_full", "flat_static", "flat_box", "flat_empty_long"), default="building")
    parser.add_argument("--building-route", choices=("short_stair", "historical_full", "corner_start"), default="short_stair")
    parser.add_argument("--integration-version")
    parser.add_argument("--goal-wall-budget", type=float, default=35.0)
    parser.add_argument("--startup-mode", choices=("policy", "pd_stand", "factory_pd"), default="policy")
    parser.add_argument("--stance-hold", action="store_true")
    parser.add_argument("--physics-backend", choices=("warp", "native"), default="warp")
    parser.add_argument("--real-time-factor", type=float, default=1.)
    parser.add_argument("--recording-sim-seconds", type=float, default=90.)
    args = parser.parse_args()
    if args.scene != "building_full" or args.real_time_factor != 1. or args.physics_backend != "warp":
        parser.error("v192 records the complete Building with the qualified CPU graph at target RTF 1")
    if not 20. <= args.recording_sim_seconds <= 600.:
        parser.error("recording-sim-seconds must be within [20,600]")
    long_route = args.scene == "flat_empty_long"
    full_building = args.scene == "building_full"
    historical_full = full_building and args.building_route == "historical_full"
    if args.building_route != "short_stair" and not full_building:
        parser.error("Historical Building route requires scene building_full")
    extended_route = long_route or full_building
    if not .1 <= args.real_time_factor <= 1.:
        parser.error("real-time-factor must be in [.1,1]")
    if args.real_time_factor != 1. and args.physics_backend != "native":
        parser.error("Explicit wall pacing requires the native CPU profile")
    if args.physics_backend == "native" and not long_route:
        parser.error("Native empty-floor backend is restricted to the explicit long route")
    if long_route and not (args.geometry_obstacles and args.stance_hold):
        parser.error("long empty route requires geometry-only planning and PD stance hold")
    if full_building and not (args.geometry_obstacles and args.stance_hold and args.startup_mode == "factory_pd"):
        parser.error("Full Building requires geometry-only planning and factory/PD stance control")
    if args.probe and extended_route:
        parser.error("Use the separate control qualification before the full long-route trial")
    if args.stance_hold and args.scene == "building":
        parser.error("PD stance adapter is qualified for explicit flat scenes only")
    if args.startup_mode == "factory_pd" and not (extended_route and args.stance_hold):
        parser.error("factory_pd requires an explicit extended route and stance hold")
    if args.startup_mode == "pd_stand" and (args.scene == "building" or not args.geometry_obstacles):
        parser.error("pd_stand is qualified only for geometry-only flat scenes")
    if args.scene == "flat_static" and not (args.geometry_obstacles and args.static_human):
        parser.error("flat_static requires geometry obstacles and a static human")
    if args.scene == "flat_box" and not args.geometry_obstacles:
        parser.error("flat_box requires geometry obstacles")
    if not 1.0 <= args.goal_wall_budget <= (1500.0 if extended_route else 400.0):
        parser.error("goal-wall-budget exceeds the declared scene limit")
    build = args.native_build.resolve()
    out = Path(os.environ["NEWTON_RUN_DIR"])
    if shutil.disk_usage(BASE).free < 10 * 1024**3:
        raise RuntimeError("Less than10GiB free")
    integration_version = verify_integration_version(out, args.integration_version)
    if integration_version != "v192":
        raise ValueError("This entry point requires frozen integration version v192")
    frozen = json.loads((VERSION / "manifest.json").read_text())
    verify_native_build(build, frozen)
    if args.geometry_obstacles:
        qualification = json.loads((VERSION / "quality.json").read_text())
        if not qualification["passed"] or qualification.get("native_packages_available", qualification.get("native_packages_built")) != 14:
            raise ValueError("Physics requires actual native component tests and 14 available packages")
        (out / "qualification_scope.json").write_text(json.dumps({
            "mode": "user_authorized_mac_original_full_route_trial" if platform.system() == "Darwin" else "user_authorized_linux_original_full_route_repetition",
            "native_component_platform": qualification["execution_platform"], "native_component_tests_passed": True, "full_component_qualification": False,
            "missing_original_corner_fixtures": ["Repeated original full-route navigation and steady 30 Hz acceptance"],
            "live_safety_gates": "original occupancy, stair support, PVA, dynamics, and direct Nav2+SCAN execution",
            "reference_version": "v48", "physics_acceptance": False,
        }, indent=2) + "\n")
    for record in json.loads((BASE / "setup/runtime_sources.json").read_text())["records"]:
        if hashlib.sha256((BASE / record["path"]).read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError("Archived runtime source changed")
    epoch = time.time_ns()
    prepare_external_directory(out)
    (out / "inputs").mkdir()
    planner_config = args.planner_config or (VERSION / ("flat_planner.yaml" if args.scene.startswith("flat_") else "building_planner.yaml"))
    expected_config = VERSION / ("flat_planner.yaml" if args.scene.startswith("flat_") else "building_planner.yaml")
    if planner_config.resolve() != expected_config.resolve():
        raise ValueError("Planner configuration must be the selected frozen v192 configuration")
    shutil.copyfile(planner_config, out / "planner.yaml")
    if args.geometry_obstacles:
        driver = BASE / "repairs/2026-09-26_generic_occupancy/geometry_driver.py"
        identity = json.loads(driver.with_name("driver_identity.json").read_text())
        if hashlib.sha256(driver.read_bytes()).hexdigest() != identity["output_sha256"]:
            raise ValueError("Geometry driver identity changed")
        shutil.copyfile(driver, out / "executed_geometry_driver.py")
    for name in ("pilot.json", "stair_scenario.json"):
        shutil.copyfile(BASE / "inputs" / name, out / "inputs" / name)
    if full_building:
        scenario_path = out / "inputs/stair_scenario.json"
        scenario = building_scenario(args.building_route, args.goal_wall_budget)
        scenario_path.write_text(json.dumps(scenario, indent=2) + "\n")
    if args.scene in ("flat_static", "flat_box", "flat_empty_long"):
        scene_root = BASE / ("repairs/2026-09-27_pd_long_route/inputs" if long_route
                             else "repairs/2026-09-26_generic_occupancy/flat_inputs_v2")
        scene_identity = json.loads((scene_root / "manifest.json").read_text())
        for name, expected in scene_identity["files"].items():
            if hashlib.sha256((scene_root / name).read_bytes()).hexdigest() != expected:
                raise ValueError("Flat scene identity mismatch")
        shutil.copyfile(scene_root / "scene.json", out / "inputs/stair_scenario.json")
        shutil.copyfile(scene_root / "manifest.json", out / "flat_scene_identity.json")
        shutil.copyfile(scene_root / "flat_floor.pickle", out / "inputs/flat_floor.pickle")
        publisher = BASE / "repairs/2026-09-26_generic_occupancy/flat_support_publisher.py"
        publisher_identity = json.loads(publisher.with_name("flat_publisher_identity.json").read_text())
        if hashlib.sha256(publisher.read_bytes()).hexdigest() != publisher_identity["output_sha256"]:
            raise ValueError("Flat support publisher identity changed")
        shutil.copyfile(publisher, out / "executed_flat_support_publisher.py")
    (out / "episode_request.json").write_text(json.dumps({"run_epoch_ns": epoch, "probe": args.probe,
        "backend_executor": args.backend_executor,
        "applied_transport": args.applied_transport,
        "native_build": str(build), "geometry_obstacles": args.geometry_obstacles,
        "scene": args.scene,
        "building_route_profile": args.building_route if full_building else None,
        "integration_version": integration_version,
        "native_variant": os.environ["V192_VARIANT"],
        "execution_host": platform.node(),
        "execution_host_platform": platform.system() + "/" + platform.machine(),
        "native_platform": qualification['execution_platform'],
        "startup_mode": args.startup_mode,
        "stance_hold": args.stance_hold,
        "body_publish_substeps": 5 if extended_route else 20,
        "async_sensor_evidence": extended_route,
        "physics_backend": args.physics_backend,
        "pace_physics_wall": True,
        "recording_preview": True,
        "real_time_factor": args.real_time_factor,
        "static_human": args.static_human,
        "goal_wall_budget_s": args.goal_wall_budget,
        "planner_config_source": str(planner_config),
        "planner_config_sha256": hashlib.sha256((out / "planner.yaml").read_bytes()).hexdigest(),
        "max_physics_s": args.recording_sim_seconds if full_building else (8 if args.startup_mode == "pd_stand" else 3) if args.probe else (150 if long_route else 600 if historical_full else 90 if full_building else 35),
        "max_worker_wall_s": args.recording_sim_seconds + 120.,
        "source_condition": "Complete original Building / explicit variant-bound PCT cost map / original sensor rig / direct Nav2 + PCT + SCAN / factory-PD-RL switching",
        "sensor_condition": "geometric emitter-owner exclusion and complete original Building triangles; no added actor; not RTX",
        "control_timing_condition": "direct Nav2 controller to /quad_0/cmd_vel; total goal wall budget recorded separately",
        "sensor_preprocessing": "unfiltered planner cloud, as archived unfiltered_planner_cloud=true"}, indent=2) + "\n")
    for path in (BASE / "scripts").glob("*.py"):
        shutil.copyfile(path, out / ("executed_" + path.name))
    shutil.copyfile(VERSION / "long_route_driver.py", out / "executed_long_route_driver.py")
    for name in ("run_local_episode.py", "native_graph.py", "navigation_contract.json", "newton_episode.py", "realtime_pacer.py", "frequency_observer.py", "native_observer.py", "nav2_recorder.py", "initial_frame_v142.py"):
        shutil.copyfile(VERSION / name, out / ("executed_v192_" + name))
    shutil.copyfile(BASE.parent / "2026-09-26_newton_macos_policy/scripts/lite3_newton.py", out / "executed_lite3_newton.py")
    if args.stance_hold:
        shutil.copyfile(BASE.parent / "2026-09-26_newton_macos_policy/scripts/newton_stance.py", out / "executed_newton_stance.py")
        shutil.copyfile(BASE.parent / "2026-09-16_pi_cortex_harnessvln/isaac_runner/stance_hold.py", out / "executed_stance_hold.py")
    if args.startup_mode == "factory_pd":
        factory = BASE.parent / "2026-09-27_lite3_factory_runtime_audit"
        for name in ("factory_process.py", "factory_actor.cpp", "prepare_algorithm_inputs.py", "run_newton_factory.py"):
            shutil.copyfile(factory / name, out / ("executed_" + name))
    if args.startup_mode == "pd_stand":
        qualified = BASE.parent / "2026-09-26_newton_macos_policy"
        shutil.copyfile(qualified / "scripts/pd_startup.py", out / "executed_pd_startup.py")
        shutil.copyfile(qualified / "runtime/lite3_sdk_spline/build_identity.json", out / "sdk_build_identity.json")
    (out / "execution_sources.json").write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in out.glob("executed_*")}, indent=2)+"\n")
    sources = BASE / "runtime_sources"
    pythonpath = "/task/foxy_python:" + str(sources / "bridge")
    script = "\n".join(["set -e", "source /opt/ros/foxy/setup.bash",
        "source /task/recovery_v176/install/setup.bash",
        "source /task/recovery_v191/install/setup.bash",
        "export PYTHONPATH=" + shlex.quote(pythonpath) + ':"${PYTHONPATH:-}"',
        "exec python3 " + shlex.quote(str(VERSION / "native_graph.py")) + " --output " + shlex.quote(str(out)), ""])
    (out / "native_inside.sh").write_text(script)
    name = os.environ["V192_NATIVE_CONTAINER"]
    command = ["docker", "exec", "-e", "V192_PHYSICAL_FLOOR=" + os.environ["V192_PHYSICAL_FLOOR"],
        name, "/bin/bash", str(out / "native_inside.sh")]
    (out / "container_command.json").write_text(json.dumps(command, indent=2) + "\n")
    with (out / "native_graph.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            worker = subprocess.run([sys.executable, str(VERSION / "newton_episode.py")], timeout=1700 if extended_route else 500)
            worker.check_returncode()
        finally:
            subprocess.run(["docker", "exec", name, "pkill", "-TERM", "-f", str(VERSION / "native_graph.py")],
                           capture_output=True, text=True, timeout=10)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate(); process.wait(timeout=5)
            from shared_state import verify_shared_state
            shared_ok = verify_shared_state(name, out)
            subprocess.run(["docker", "stop", "--time", "5", name],capture_output=True,text=True,timeout=15)
            subprocess.run(["docker", "rm", "-f", name],capture_output=True,text=True,timeout=15)
            if not shared_ok:
                raise RuntimeError("Shared-state verification failed; see shared_state.json")


if __name__ == "__main__":
    main()
