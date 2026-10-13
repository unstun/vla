"""Bounded real launch/lifecycle/parameter smoke with TF only, zero route requests."""
import json
import os
from pathlib import Path
import signal
import subprocess

import rclpy
from lifecycle_msgs.srv import GetState
from rcl_interfaces.srv import GetParameters
from server_probe import Probe


def main():
    destination = Path(os.environ["V86_LAUNCH_RESULT"])
    destination.mkdir(parents=True, exist_ok=False)
    result = {"passed": False, "scope": "real packaged launch and owned native mapper lifecycle; synthetic TF only",
              "route_requests": 0, "robot_actuation": False}
    log = (destination / "launch.log").open("w")
    process = subprocess.Popen([
        "ros2", "launch", "scan_nav2_controller", "scan_nav2.launch.py",
        "native_planner_config:=" + os.environ["V86_NATIVE_PARAMS"], "use_sim_time:=false",
    ], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    rclpy.init()
    node = Probe()
    try:
        state = node.create_client(GetState, "/controller_server/get_state")
        node.wait(state.service_is_ready, 15.0)
        active = False
        for _ in range(100):
            future = state.call_async(GetState.Request())
            node.wait(future.done)
            if future.result().current_state.id == 3:
                active = True
                break
            node.pause(0.1)
        assert active, "Packaged launch did not activate ControllerServer"
        parameters = node.create_client(GetParameters, "/quad_0/scan_planner_node/get_parameters")
        node.wait(parameters.service_is_ready)
        request = GetParameters.Request()
        request.names = ["grid_map.mapping_admission", "grid_map.map_update_frequency",
                         "grid_map.observation_persistence", "fsm.navi_mode"]
        future = parameters.call_async(request)
        node.wait(future.done)
        values = future.result().values
        assert values[0].string_value == "nav2_observation_window"
        assert values[1].double_value == 5.0
        assert values[2].double_value == 0.5
        assert values[3].integer_value == 3
        node.pause(0.2)
        assert not node.raw and not node.plain, "Activation emitted a motion command without a route"
        node.transition(4)
        node.transition(2)
        node.pause(0.05)
        assert not node.raw and not node.plain, "Unowned shutdown bypassed the tagged output boundary"
        result.update(passed=True, controller_active=True, native_mapper="nav2_observation_window",
                      map_update_hz=5.0, observation_persistence_s=0.5,
                      raw_commands=len(node.raw), plain_commands=len(node.plain),
                      deactivation_and_cleanup=True)
    except Exception as error:
        result["error"] = repr(error)
        raise
    finally:
        (destination / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        node.action.destroy()
        node.action = None
        node.destroy_node()
        rclpy.shutdown()
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
        log.close()


if __name__ == "__main__":
    main()
