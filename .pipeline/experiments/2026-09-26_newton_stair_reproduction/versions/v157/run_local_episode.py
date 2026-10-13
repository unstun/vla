"""Own one local native-ROS container and one bounded Newton episode."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
import time

VERSION = Path(__file__).resolve().parent
BASE = VERSION.parents[1]
PROJECT = BASE.parents[2]
BUILD = VERSION
IMAGE = os.environ.get("V157_EXECUTION_IMAGE")  # The owned launcher pins the qualified Foxy image.


def return_linux_state(name, out):
    """Read the mounted tmpfs, using Docker's documented exec/tar method."""
    returned = out / "returned_external_episode"
    returned.mkdir(exist_ok=True)
    archive = out / "linux_external_episode.tar"
    receipt = {"method": "docker exec tar", "verified": False,
        "reference": "https://docs.docker.com/reference/cli/docker/container/cp/#corner-cases"}
    try:
        with archive.open("wb") as stream:
            copied = subprocess.run(["docker", "exec", name, "tar", "-C",
                str(out / "artifacts/external_episode"), "-cf", "-", "."],
                stdout=stream, stderr=subprocess.PIPE, timeout=15)
        receipt.update(exit_code=copied.returncode, stderr=copied.stderr.decode(errors="replace"))
        copied.check_returncode()
        with tarfile.open(archive) as bundle:
            for member in bundle:
                if member.isdir():
                    continue
                target = returned / member.name
                if (not member.isfile() or member.size > 8 * 1024**2
                        or not target.resolve().is_relative_to(returned.resolve())):
                    raise ValueError("Unexpected state archive member: " + member.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as source:
                    target.write_bytes(source.read())
        hashes = {str(p.relative_to(returned)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in returned.rglob("*") if p.is_file()}
        audit = returned / "applied_channel.jsonl"
        if not audit.is_file():
            raise ValueError("Missing returned Linux applied-state audit")
        shutil.copyfile(audit, out / "applied_channel.jsonl")
        last_ack = None
        with (out / "applied_sent.jsonl").open() as sent:
            for line in sent:
                last_ack = json.loads(line)["ack"]
        receipt.update(files_sha256=hashes, last_ack=last_ack,
                       archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
        if last_ack is None or hashes.get("current_command.json") != last_ack["sha256"]:
            raise ValueError("Returned Linux state does not match the last acknowledged bytes")
        receipt["verified"] = True
    except Exception as error:
        receipt["error"] = repr(error)
    (out / "state_copyback.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt["verified"]


def verify_integration_version(out, version=None):
    """Bind new runs to a frozen local integration snapshot, not a dirty Git tag."""
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
    external=out / "artifacts/external_episode"
    if external.exists() and (external.is_symlink() or not external.is_dir() or any(external.iterdir())):
        raise FileExistsError("Applied-state storage already contains data: " + str(external))
    external.mkdir(parents=True,exist_ok=True)


def building_scenario(profile, wall_budget):
    """Select an explicit immutable route profile within the same Building."""
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
    parser.add_argument("--applied-transport", choices=("shared", "zmq"), default="shared")
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
        parser.error("v157 records the complete Building with the qualified CPU graph at target RTF 1")
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
    if integration_version != "v157":
        raise ValueError("This entry point requires frozen integration version v157")
    frozen = json.loads((VERSION / "manifest.json").read_text())
    verify_native_build(build, frozen)
    if args.geometry_obstacles:
        qualification = json.loads((VERSION / "quality.json").read_text())
        if not qualification["passed"] or qualification.get("native_packages_available", qualification.get("native_packages_built")) != 14:
            raise ValueError("Mac diagnostic physics requires actual native component tests")
        (out / "qualification_scope.json").write_text(json.dumps({
            "mode": "user_authorized_mac_original_full_route_diagnosis",
            "arm64_component_subset_passed": True, "full_component_qualification": False,
            "missing_original_corner_fixtures": ["Repeated original full-route navigation and steady 30 Hz acceptance"],
            "live_safety_gates": "original occupancy, stair support, PVA, dynamics, freshness and backend stop gates",
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
        raise ValueError("Planner configuration must be the selected frozen v157 configuration")
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
        "native_variant": os.environ["V157_VARIANT"],
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
        "source_condition": ("Complete original Building / explicit variant-bound PCT cost map / original sensor rig / PCT + SCAN / factory-PD-RL switching"
                             if full_building else "12 m empty flat scene / original sensor rig / native PCT + SCAN42 + controller / PD-RL switching"
                             if long_route else "flat scene / unclassified box / original sensor rig; native PCT/SCAN/controller; no obstacle metadata"
                             if args.scene == "flat_box" else "flat scene / stationary official human / original sensor rig; native PCT/SCAN/controller; no obstacle metadata"
                             if args.scene == "flat_static" else "original Building/sensor rig; native geometry-only SCAN candidate, unchanged PCT/controller"
                             if args.geometry_obstacles else "original Building/right official human/sensor rig; unchanged PCT/SCAN/controller/tracker"),
        "sensor_condition": ("geometric emitter-owner exclusion and complete original Building triangles; no added actor; not RTX"
                             if full_building else "geometric emitter-owner exclusion and physical floor; no obstacle or human mesh; not RTX"
                             if long_route else "geometric emitter-owner exclusion and actual static box geometry; no human mesh; not RTX"
                             if args.scene == "flat_box" else "geometric emitter-owner exclusion and authored visible human meshes; not RTX"
                             if args.geometry_obstacles else "qualified geometric emitter-owner exclusion, not RTX"),
        "control_timing_condition": "original sensor/command freshness watchdogs and MAVROS-derived clock mapping; total goal wall budget recorded separately",
        "sensor_preprocessing": "unfiltered planner cloud, as archived unfiltered_planner_cloud=true"}, indent=2) + "\n")
    for path in (BASE / "scripts").glob("*.py"):
        shutil.copyfile(path, out / ("executed_" + path.name))
    shutil.copyfile(VERSION / "long_route_driver.py", out / "executed_long_route_driver.py")
    for name in ("run_local_episode.py", "native_graph.py", "navigation_contract.json", "newton_episode.py", "realtime_pacer.py", "frequency_observer.py", "native_observer.py", "nav2_recorder.py", "initial_frame_v142.py"):
        shutil.copyfile(VERSION / name, out / ("executed_v157_" + name))
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
        "source /task/" + ("recovery_v139_02" if os.environ["V157_VARIANT"] == "baseline" else "recovery_v157") + "/install/setup.bash",
        "export PYTHONPATH=" + shlex.quote(pythonpath) + ':"${PYTHONPATH:-}"',
        "exec python3 " + shlex.quote(str(VERSION / "native_graph.py")) + " --output " + shlex.quote(str(out)), ""])
    (out / "native_inside.sh").write_text(script)
    name = "vla-newton-" + out.name.replace("_", "-")
    name = os.environ["V157_NATIVE_CONTAINER"]
    command = ["docker", "exec", "-e", "V157_PHYSICAL_FLOOR=" + os.environ["V157_PHYSICAL_FLOOR"],
        name, "/bin/bash", str(out / "native_inside.sh")]
    (out / "container_command.json").write_text(json.dumps(command, indent=2) + "\n")
    with (out / "native_graph.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            worker = subprocess.run([sys.executable, str(VERSION / "newton_episode.py")], timeout=1700 if extended_route else 500)
            worker.check_returncode()
        finally:
            copyback_ok = True
            if args.applied_transport == "zmq":
                copyback_ok = return_linux_state(name, out)
            subprocess.run(["docker", "exec", name, "pkill", "-TERM", "-f", str(VERSION / "native_graph.py")],
                           capture_output=True, text=True, timeout=10)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate(); process.wait(timeout=5)
            # ros2 run can leave native descendants after its wrapper exits.
            # Original runtime-container teardown closes all owned writers
            # before the managed supervisor verifies closed-run retention.
            subprocess.run(["docker", "stop", "--time", "5", name],capture_output=True,text=True,timeout=15)
            subprocess.run(["docker", "rm", "-f", name],capture_output=True,text=True,timeout=15)
            if not copyback_ok:
                raise RuntimeError("Linux state copyback failed verification; see state_copyback.json")


if __name__ == "__main__":
    main()
