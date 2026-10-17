"""ROS-free regression for sidecar cleanup after executor shutdown."""

import ast
from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name("pct_sim_clock_publisher.py")


class ExternalShutdownException(Exception):
    pass


def main_from_source(ros, constructor):
    tree = ast.parse(SOURCE.read_text())
    main = next(node for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == "main")
    namespace = {
        "rclpy": ros,
        "PctSimClockPublisher": constructor,
        "ExternalShutdownException": ExternalShutdownException,
    }
    exec(compile(ast.Module(body=[main], type_ignores=[]), str(SOURCE), "exec"),
         namespace)
    return namespace["main"]


class FakeNode:
    def __init__(self, events):
        self.events = events

    def destroy_node(self):
        self.events.append("destroy")


class FakeRclpy:
    def __init__(self, events, spin_result):
        self.events = events
        self.spin_result = spin_result
        self.active = False

    def init(self, args=None):
        self.events.append("init")
        self.active = True

    def spin(self, node):
        self.events.append("spin")
        if self.spin_result == "external_shutdown":
            self.active = False
            raise ExternalShutdownException()
        if self.spin_result == "keyboard_interrupt":
            raise KeyboardInterrupt()

    def ok(self):
        self.events.append("ok")
        return self.active

    def shutdown(self):
        if not self.active:
            raise RuntimeError("context was already shut down")
        self.events.append("shutdown")
        self.active = False


class ShutdownTest(unittest.TestCase):
    def test_external_shutdown_does_not_shutdown_context_twice(self):
        events = []
        ros = FakeRclpy(events, "external_shutdown")
        main_from_source(ros, lambda: FakeNode(events))()
        self.assertEqual(events, ["init", "spin", "destroy", "ok"])

    def test_normal_return_shuts_down_once(self):
        events = []
        ros = FakeRclpy(events, "return")
        main_from_source(ros, lambda: FakeNode(events))()
        self.assertEqual(events, ["init", "spin", "destroy", "ok", "shutdown"])

    def test_keyboard_interrupt_shuts_down_once(self):
        events = []
        ros = FakeRclpy(events, "keyboard_interrupt")
        main_from_source(ros, lambda: FakeNode(events))()
        self.assertEqual(events, ["init", "spin", "destroy", "ok", "shutdown"])


if __name__ == "__main__":
    unittest.main()
