"""Regression checks for the event boundary that supplies MIP scoring facts."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest

# Event parsing is dependency-free; the remote smoke exercises the real driver.
saved = sys.modules.get("driver")
sys.modules["driver"] = types.SimpleNamespace(SessionOutcome=object)
spec = importlib.util.spec_from_file_location(
    "deepseek_adapter_under_test", Path(__file__).with_name("deepseek_adapter.py"))
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
if saved is None:
    del sys.modules["driver"]
else:
    sys.modules["driver"] = saved


class Recorder:
    def __init__(self):
        self.events = []

    def emit(self, kind, data):
        self.events.append((kind, data))


class EventBoundaryTest(unittest.TestCase):
    def parse(self, events):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text(''.join(json.dumps(e) + '\n' for e in events))
            sink = Recorder()
            result = adapter.replay_events(path, sink)
        return result, sink.events

    def test_stop_facts_survive_nested_result(self):
        text = json.dumps({"steps_taken_total": 2, "end_reason": "stop_called"})
        result, events = self.parse([
            {"type": "tool/call", "data": {"name": "mcp__env__step",
                "callId": "x", "arguments": '{"actions":[0]}'}},
            {"type": "tool/result", "data": {"message": {"content": [
                {"type": "tool-result", "content": [{"type": "text", "text": text},
                                                        {"type": "image", "data": "blob"}]}]}}},
            {"type": "turn/end", "data": {"reason": {"kind": "completed"}}},
        ])
        self.assertEqual(events[1][1]["texts"], [text])
        self.assertEqual(result[0], {"kind": "completed"})

    def test_host_tool_in_request_fails(self):
        with self.assertRaisesRegex(RuntimeError, "Unexpected model-visible"):
            self.parse([{"type": "request/header", "data": {"header": {
                "tools": [{"name": "mcp__env__observe"}, {"name": "bash"}]}}}])

    def test_no_final_event_is_not_completed(self):
        result, _ = self.parse([{"type": "step/start", "data": {"step": 1}}])
        self.assertIsNone(result[0])
        self.assertEqual(result[1], 1)


if __name__ == "__main__":
    unittest.main()
