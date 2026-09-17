"""Offline navigation contract probe. Fixture evidence is NOT robot/simulator data."""

import copy
import json
import math
import time


def tool(name, description, *fields):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "additionalProperties": False,
                       "properties": {key: {"type": "string", "minLength": 1,
                                            "maxLength": 200} for key in fields},
                       "required": list(fields)},
    }}


TOOLS = [
    tool("observe", "Refresh current observation and task evidence."),
    tool("observe_panorama", "Get a fixture panorama, not rendered imagery."),
    tool("retrieve_memory", "Read recorded events and visited places; no ST Graph yet."),
    tool("ground_target", "Ground a visible label for the active subgoal.",
         "label", "observation_id", "subgoal_id"),
    tool("query_depth", "Query fixture geometric distance, not RGB-D depth.",
         "target_id", "observation_id"),
    tool("navigate_to", "Execute one validated grounded target.",
         "target_id", "observation_id", "subgoal_id"),
    tool("backtrack", "Return to a recorded visited place.", "place_id", "observation_id"),
    tool("request_stop", "Request evidence-checked task termination.", "observation_id"),
]
SCHEMAS = {item["function"]["name"]: item["function"]["parameters"] for item in TOOLS}
MUTATING = {"navigate_to", "backtrack", "request_stop"}


class Rejected(Exception):
    pass


class FixtureWorld:
    """Injectable deterministic executor. It performs no network or robot I/O."""

    def __init__(self, blocked=(), fail_next=False):
        self.position = [0.0, 0.0]
        self.detections = {"doorway": [1.0, 0.0], "table": [2.0, 0.0]}
        self.blocked = set(blocked)
        self.fail_next = fail_next
        self.moves = 0

    def move(self, position):
        self.moves += 1
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("injected_executor_failure")
        self.position = list(position)
        return {"position_m": list(self.position), "frame": "fixture_map"}

    def matches(self, label):
        return label in self.detections and math.dist(self.position, self.detections[label]) <= 0.1


class Gateway:
    def __init__(self, run_id="offline-fixture", world=None, clock=time.monotonic, max_age=10.0):
        self.run_id, self.world, self.clock, self.max_age = run_id, world or FixtureWorld(), clock, max_age
        self.revision = 0
        self.observation = None
        self.observation_count = 0
        self.targets = {}
        self.events = []
        self.cache = {}
        self.last_decision = 0
        self.operation_used = False
        self.terminal = False
        self.places = {"place-0": list(self.world.position)}
        self.subgoals = [
            {"id": "sg-1", "label": "doorway", "status": "active", "evidence": None},
            {"id": "sg-2", "label": "table", "status": "pending", "evidence": None},
        ]

    def context(self):
        # Explicit projection; never serialize an executor/evaluator __dict__.
        return copy.deepcopy({"run_id": self.run_id, "revision": self.revision,
                              "evidence_kind": "deterministic_fixture",
                              "subgoals": self.subgoals, "observation": self.observation,
                              "terminal": self.terminal})

    def fresh(self, observation_id):
        obs = self.observation
        if not obs or observation_id != obs["id"] or obs["revision"] != self.revision:
            raise Rejected("stale_or_unknown_observation")
        if self.clock() - obs["captured_monotonic"] > self.max_age:
            raise Rejected("expired_observation")
        return obs

    def active(self, subgoal_id):
        for subgoal in self.subgoals:
            if subgoal["id"] == subgoal_id and subgoal["status"] == "active":
                return subgoal
        raise Rejected("inactive_subgoal")

    def target(self, args):
        self.fresh(args["observation_id"])
        target = self.targets.get(args["target_id"])
        if not target or target["observation_id"] != args["observation_id"] or target["revision"] != self.revision:
            raise Rejected("stale_or_unknown_target")
        return target

    def observe(self, panorama=False):
        self.observation_count += 1
        self.observation = {"id": f"obs-{self.observation_count}", "revision": self.revision,
                            "captured_monotonic": self.clock(), "frame": "fixture_map",
                            "position_m": list(self.world.position),
                            "visible_labels": list(self.world.detections), "panorama": panorama,
                            "evidence_kind": "deterministic_fixture"}
        for index, subgoal in enumerate(self.subgoals):
            if subgoal["status"] == "active" and self.world.matches(subgoal["label"]):
                subgoal.update(status="completed", evidence=self.observation["id"])
                if index + 1 < len(self.subgoals):
                    self.subgoals[index + 1]["status"] = "active"
                break
        return copy.deepcopy(self.observation)

    def execute(self, name, args):
        if name in {"observe", "observe_panorama"}:
            return self.observe(name == "observe_panorama")
        if name == "retrieve_memory":
            return {"events": copy.deepcopy(self.events[-8:]),
                    "visited_places": copy.deepcopy(self.places), "memory_kind": "event_fixture_not_st_graph"}
        if name == "ground_target":
            obs = self.fresh(args["observation_id"])
            active = self.active(args["subgoal_id"])
            if args["label"] not in obs["visible_labels"] or args["label"] != active["label"]:
                raise Rejected("unsupported_target_evidence")
            key = f"target-{len(self.targets) + 1}"
            target = {"id": key, "label": args["label"], "observation_id": obs["id"],
                      "revision": self.revision, "subgoal_id": active["id"], "frame": "fixture_map",
                      "position_m": list(self.world.detections[args["label"]])}
            self.targets[key] = target
            return copy.deepcopy(target)
        if name == "query_depth":
            target = self.target(args)
            return {"fixture_distance_m": math.dist(self.world.position, target["position_m"]),
                    "evidence_kind": "fixture_geometry_not_depth_sensor"}
        if name == "navigate_to":
            target = self.target(args)
            self.active(args["subgoal_id"])
            if target["subgoal_id"] != args["subgoal_id"]:
                raise Rejected("target_subgoal_mismatch")
            if target["label"] in self.world.blocked:
                raise Rejected("unreachable_target")
            destination = target["position_m"]
        elif name == "backtrack":
            self.fresh(args["observation_id"])
            if args["place_id"] not in self.places:
                raise Rejected("unknown_place")
            destination = self.places[args["place_id"]]
        elif name == "request_stop":
            self.fresh(args["observation_id"])
            if not all(s["status"] == "completed" for s in self.subgoals):
                raise Rejected("incomplete_task")
            if not self.world.matches(self.subgoals[-1]["label"]):
                raise Rejected("unverified_stop_geometry_or_semantics")
            self.terminal = True
            return {"terminal_cause": "accepted_fixture_stop", "evidence": args["observation_id"]}
        else:
            raise Rejected("unknown_tool")
        # Invalidate even if the executor fails after possibly starting motion.
        self.revision += 1
        self.observation = None
        result = self.world.move(destination)
        self.places[f"place-{len(self.places)}"] = list(self.world.position)
        return result

    def dispatch(self, request):
        if not isinstance(request, dict) or set(request) != {"run_id", "call_id", "decision_id", "tool", "arguments"}:
            return {"ok": False, "status": "rejected", "error": "invalid_envelope", "state": self.context()}
        call_id, name, args, decision = (request[k] for k in ("call_id", "tool", "arguments", "decision_id"))
        if not isinstance(call_id, str) or not 1 <= len(call_id) <= 200:
            return {"ok": False, "status": "rejected", "error": "invalid_call_id", "state": self.context()}
        fingerprint = json.dumps(request, sort_keys=True, allow_nan=False)
        if call_id in self.cache:
            saved_request, result = self.cache[call_id]
            if saved_request != fingerprint:
                return {"ok": False, "status": "rejected", "error": "call_id_conflict", "state": self.context()}
            return copy.deepcopy(result)
        result = {"ok": False, "status": "rejected"}
        try:
            if len(self.cache) >= 128:
                raise Rejected("tool_budget_exhausted")
            if request["run_id"] != self.run_id:
                raise Rejected("wrong_run")
            if type(decision) is not int or decision < 1 or decision < self.last_decision:
                raise Rejected("stale_or_invalid_decision")
            if decision > self.last_decision:
                self.last_decision, self.operation_used = decision, False
            if not isinstance(name, str) or name not in SCHEMAS:
                raise Rejected("unknown_tool")
            schema = SCHEMAS[name]
            if not isinstance(args, dict) or set(args) != set(schema["required"]):
                raise Rejected("invalid_arguments")
            if any(not isinstance(value, str) or not 1 <= len(value) <= 200 for value in args.values()):
                raise Rejected("invalid_arguments")
            if self.terminal:
                raise Rejected("episode_terminated")
            if name in MUTATING:
                if self.operation_used:
                    raise Rejected("one_operation_per_decision")
                self.operation_used = True
            result.update(ok=True, status="ok", data=self.execute(name, args))
        except Rejected as error:
            result["error"] = str(error)
        except RuntimeError as error:
            result.update(status="failed", error=str(error))
        result["state"] = self.context()
        self.events.append({"seq": len(self.events) + 1, "call_id": call_id,
                            "decision_id": decision, "tool": name, "status": result["status"],
                            "error": result.get("error"), "revision": self.revision})
        self.cache[call_id] = fingerprint, copy.deepcopy(result)
        return result
