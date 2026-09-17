import json
import unittest

from gateway import FixtureWorld, Gateway


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.gateway = Gateway()
        self.counter = 0

    def call(self, name, args=None, decision=None, **extra):
        self.counter += 1
        request = {"run_id": self.gateway.run_id, "call_id": f"test-{self.counter}",
                   "decision_id": self.counter if decision is None else decision,
                   "tool": name, "arguments": args or {}}
        request.update(extra)
        return self.gateway.dispatch(request)

    def ground(self, label="doorway", subgoal="sg-1"):
        obs = self.call("observe")["data"]["id"]
        target = self.call("ground_target", {"label": label, "observation_id": obs,
                                              "subgoal_id": subgoal})
        self.assertTrue(target["ok"], target)
        return {"target_id": target["data"]["id"], "observation_id": obs, "subgoal_id": subgoal}

    def reach_end(self):
        for label, subgoal in [("doorway", "sg-1"), ("table", "sg-2")]:
            args = self.ground(label, subgoal)
            self.assertTrue(self.call("navigate_to", args)["ok"])
            self.assertTrue(self.call("observe")["ok"])

    def test_completion_requires_new_observation_then_stop(self):
        args = self.ground()
        result = self.call("navigate_to", args)
        self.assertTrue(result["ok"])
        self.assertEqual(result["state"]["subgoals"][0]["status"], "active")
        self.call("observe")
        self.assertEqual(self.gateway.subgoals[0]["evidence"], "obs-2")
        args = self.ground("table", "sg-2")
        self.call("navigate_to", args)
        observed = self.call("observe")["data"]["id"]
        result = self.call("request_stop", {"observation_id": observed})
        self.assertTrue(result["state"]["terminal"])
        self.assertEqual(self.gateway.world.moves, 2)
        self.assertEqual(self.call("backtrack", {"place_id": "place-0", "observation_id": observed})["error"],
                         "episode_terminated")

    def test_premature_stop_and_forged_predicate_rejected(self):
        self.call("observe")
        self.assertEqual(self.call("request_stop", {"observation_id": "obs-1"})["error"], "incomplete_task")
        result = self.call("request_stop", {"observation_id": "obs-1", "verified": True})
        self.assertEqual(result["error"], "invalid_arguments")
        self.assertFalse(self.gateway.terminal)

    def test_stale_after_motion_and_expired_evidence(self):
        args = self.ground()
        self.call("navigate_to", args)
        self.assertEqual(self.call("navigate_to", args)["error"], "stale_or_unknown_observation")
        now = [0.0]
        self.gateway = Gateway(clock=lambda: now[0], max_age=10)
        args = self.ground()
        now[0] = 11
        self.assertEqual(self.call("navigate_to", args)["error"], "expired_observation")
        self.assertEqual(self.gateway.world.moves, 0)

    def test_inactive_subgoal_and_unsupported_label(self):
        self.call("observe")
        result = self.call("ground_target", {"label": "table", "observation_id": "obs-1", "subgoal_id": "sg-2"})
        self.assertEqual(result["error"], "inactive_subgoal")
        result = self.call("ground_target", {"label": "imaginary", "observation_id": "obs-1", "subgoal_id": "sg-1"})
        self.assertEqual(result["error"], "unsupported_target_evidence")

    def test_unreachable_target_cannot_move(self):
        self.gateway = Gateway(world=FixtureWorld(blocked={"doorway"}))
        args = self.ground()
        self.assertEqual(self.call("navigate_to", args)["error"], "unreachable_target")
        self.assertEqual(self.gateway.world.moves, 0)

    def test_failed_execution_invalidates_evidence_without_completion(self):
        self.gateway = Gateway(world=FixtureWorld(fail_next=True))
        args = self.ground()
        result = self.call("navigate_to", args)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["ok"])
        self.assertIsNone(result["state"]["observation"])
        self.assertEqual(result["state"]["subgoals"][0]["status"], "active")
        self.assertEqual(self.call("navigate_to", args)["error"], "stale_or_unknown_observation")
        memory = self.call("retrieve_memory")["data"]
        self.assertIn("injected_executor_failure", json.dumps(memory))

    def test_duplicate_call_is_idempotent_and_conflict_rejected(self):
        args = self.ground()
        request = {"run_id": self.gateway.run_id, "call_id": "duplicate", "decision_id": 10,
                   "tool": "navigate_to", "arguments": args}
        first = self.gateway.dispatch(request)
        self.assertTrue(first["ok"])
        self.assertEqual(self.gateway.dispatch(request), first)
        self.assertEqual(self.gateway.world.moves, 1)
        conflict = {**request, "arguments": {**args, "target_id": "forged"}}
        self.assertEqual(self.gateway.dispatch(conflict)["error"], "call_id_conflict")
        self.assertEqual(self.gateway.world.moves, 1)

    def test_backend_independently_rejects_two_operations_per_decision(self):
        args = self.ground()
        self.call("navigate_to", args, decision=10)
        result = self.call("backtrack", {"place_id": "place-0", "observation_id": "obs-1"}, decision=10)
        self.assertEqual(result["error"], "one_operation_per_decision")
        self.assertEqual(self.gateway.world.moves, 1)

    def test_raw_tools_run_mismatch_and_old_decision(self):
        for name in ["step", "STOP", "update_parameter", "send_goal_to_controller"]:
            self.assertEqual(self.call(name)["error"], "unknown_tool")
        self.assertEqual(self.call("observe", run_id="other-run")["error"], "wrong_run")
        self.call("observe", decision=20)
        self.assertEqual(self.call("observe", decision=19)["error"], "stale_or_invalid_decision")
        self.assertEqual(self.call("observe", decision=True)["error"], "stale_or_invalid_decision")

    def test_stop_rechecks_geometry_after_backtrack(self):
        self.reach_end()
        obs = self.gateway.observation["id"]
        self.assertTrue(self.call("backtrack", {"place_id": "place-0", "observation_id": obs})["ok"])
        obs = self.call("observe")["data"]["id"]
        result = self.call("request_stop", {"observation_id": obs})
        self.assertEqual(result["error"], "unverified_stop_geometry_or_semantics")
        self.assertFalse(self.gateway.terminal)

    def test_state_projection_excludes_private_evaluator_data(self):
        self.gateway.world.evaluator = {"goal_position": [99, 99], "spl": 1.0, "secret": "evaluator-only"}
        self.call("observe")
        projected = json.dumps(self.gateway.context())
        self.assertNotIn("evaluator-only", projected)
        self.assertNotIn("goal_position", projected)


if __name__ == "__main__":
    unittest.main()
