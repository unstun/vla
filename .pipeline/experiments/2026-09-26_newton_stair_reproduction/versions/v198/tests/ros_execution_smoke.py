"""Real TCP -> Foxy bridge -> typed ROS subscriber. No simulator or nav goal."""
from dataclasses import replace
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime/bridge"))
import rclpy
from rclpy.executors import SingleThreadedExecutor
from lite3_nav2_interfaces.msg import RobotExecutionState
from lite3_sim_bridge.foxy_bridge_node import FoxyBridgeNode
from lite3_sim_bridge.execution_state import ExecutionStateV1, StanceMode, encode_execution_state_payload
from lite3_sim_bridge.protocol import BodyStateV2, MessageType, encode_frame, encode_body_state_v2_payload
from lite3_sim_bridge.transport import TelemetryPublisherServer


def main():
    telemetry = TelemetryPublisherServer(port=0, priority_send=True)
    telemetry.start()
    rclpy.init(args=["--ros-args", "-p", "telemetry_port:=" + str(telemetry.endpoint[1]),
                    "-p", "command_port:=9", "-p", "require_complete_body_state:=true",
                    "-p", "publish_clock:=true"])
    bridge = FoxyBridgeNode()
    observer = rclpy.create_node("execution_state_observer")
    messages = []
    observer.create_subscription(RobotExecutionState, "/quad_0/execution_state", messages.append, 10)
    executor = SingleThreadedExecutor()
    executor.add_node(bridge)
    executor.add_node(observer)
    sequence = 0

    def spin(duration):
        end = time.monotonic() + duration
        while time.monotonic() < end:
            executor.spin_once(timeout_sec=0.005)

    def send(kind, state, codec):
        nonlocal sequence
        sequence += 1
        assert telemetry.publish(encode_frame(kind, sequence, state.simulation_time_ns, codec(state)))

    def body(stamp, state_sequence):
        state = BodyStateV2((1., 2., 3.), (0., 0., 0., 1.), (0., 0., 0.),
            (0., 0., 0.), (0., 0., 0.), (0., 0., 0.), stamp, state_sequence, 800)
        send(MessageType.BODY_STATE_V2, state, encode_body_state_v2_payload)

    def execution(state):
        send(MessageType.EXECUTION_STATE_V1, state, encode_execution_state_payload)

    try:
        deadline = time.monotonic() + 5
        while (telemetry.stats().accepted_connections == 0 or
               bridge._execution_state_publisher.get_subscription_count() == 0):
            assert time.monotonic() < deadline, "ROS/TCP discovery timed out"
            spin(.02)
        state = ExecutionStateV1(3_000_000_000, 150, 800, 90, StanceMode.RL,
            True, True, False, (.12, -.03, .01), (.01, -.02, .08), (0., 0., 0.))
        # A foreign first execution sample must not poison the stream identity.
        body(state.simulation_time_ns, 150)
        execution(replace(state, run_epoch_ns=900))
        execution(state)
        spin(.1)
        assert len(messages) == 1, len(messages)
        msg = messages[-1]
        assert msg.stance_mode == RobotExecutionState.RL and msg.policy_owns_joints
        assert msg.measured_velocity.linear.x == .12 and msg.measured_velocity.angular.z == .08
        assert msg.header.frame_id == "base" and msg.header.stamp.sec == 3
        assert msg.state_sequence == 150 and msg.run_epoch_ns == 800 and msg.command_sequence == 90
        # Fresh wire sequence cannot turn duplicates, foreign runs or frozen
        # source time into fresh execution state.
        execution(state)
        execution(replace(state, state_sequence=151, simulation_time_ns=3_020_000_000, run_epoch_ns=900))
        execution(replace(state, state_sequence=151))
        spin(.1)
        assert len(messages) == 1
        stand = replace(state, simulation_time_ns=3_020_000_000, state_sequence=151,
                        stance_mode=StanceMode.FIXED_STAND, policy_owns_joints=False)
        body(stand.simulation_time_ns, 151)
        execution(stand)
        spin(.1)
        assert len(messages) == 2 and not messages[-1].policy_owns_joints
        assert messages[-1].stance_mode == RobotExecutionState.FIXED_STAND
        # Data arriving behind the current physics clock is not re-stamped.
        body(4_000_000_000, 200)
        execution(replace(stand, simulation_time_ns=3_040_000_000, state_sequence=152))
        spin(.1)
        assert len(messages) == 2
        # Wall-time queue delay and an idle publisher also cannot refresh state.
        fresh = replace(stand, simulation_time_ns=4_000_000_000, state_sequence=200)
        execution(fresh)
        deadline = time.monotonic() + 1
        while bridge._execution_state.latest_simulation_time_ns != 4_000_000_000:
            assert time.monotonic() < deadline
            time.sleep(.005)
        time.sleep(.07)
        spin(.15)
        assert len(messages) == 2
        print(json.dumps({"passed": True, "received_samples": len(messages),
            "cases": ["socket_to_typed_ros", "zero_command_keeps_rl_ownership",
                      "fixed_stand_pd", "duplicate_rejected", "foreign_run_rejected",
                      "foreign_first_sample_does_not_poison", "frozen_source_time_rejected",
                      "old_source_time_dropped", "wall_queue_delay_dropped", "no_timer_republication"],
            "physics_steps": 0, "navigation_goals": 0}))
    finally:
        executor.shutdown()
        bridge.destroy_node()
        observer.destroy_node()
        rclpy.shutdown()
        telemetry.stop()


if __name__ == "__main__":
    main()
