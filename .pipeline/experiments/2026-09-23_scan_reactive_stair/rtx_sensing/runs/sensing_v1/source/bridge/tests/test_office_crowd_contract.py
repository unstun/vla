import json
import math
from pathlib import Path
import unittest

import yaml

from lite3_sim_bridge.office_crowd_contract import (
    OfficePedestrianRoute,
    office_pedestrian_state,
    pairwise_clearance_precheck,
    routes_from_preflight,
)


class OfficeCrowdContractTest(unittest.TestCase):
    def test_route_planner_and_acceptance_waypoints_are_identical(self):
        root = Path(__file__).resolve().parents[3]
        experiment = (
            root
            / ".pipeline/experiments/2026-08-17_office_l0_scan_crowd"
        )
        route = json.loads(
            (experiment / "office_l0_route_preflight07.json").read_text()
        )
        thresholds = json.loads(
            (experiment / "acceptance_thresholds_office_crowd.json").read_text()
        )
        planner = yaml.safe_load(
            (
                root
                / "integration/scan_planner_foxy_ws/src/plan_manage/config/foxy_isaac_office_crowd_planner.yaml"
            ).read_text()
        )
        flat_waypoints = planner["scan_planner_node"]["ros__parameters"][
            "fsm.waypoints"
        ]
        planner_waypoints = [
            flat_waypoints[index : index + 3]
            for index in range(0, len(flat_waypoints), 3)
        ]

        self.assertEqual(
            planner_waypoints, route["scan_sparse_waypoints_xyz_m"]
        )
        self.assertEqual(
            thresholds["sparse_waypoints_world_xyz_m"],
            route["scan_sparse_waypoints_xyz_m"],
        )
        self.assertEqual(
            thresholds["scene"]["route_preflight_sha256"],
            "6e0db6f6803483fba846a515225aa167aaf7182fe645db11a5da02518cccf368",
        )

    def test_one_shot_route_waits_walks_and_stops(self):
        route = OfficePedestrianRoute("person", (0.0, 0.0), (2.0, 0.0), 1.0, 1.0)
        self.assertEqual(office_pedestrian_state(0.5, route)["phase"], "waiting")
        self.assertEqual(office_pedestrian_state(2.0, route)["xy_m"], (1.0, 0.0))
        self.assertEqual(office_pedestrian_state(5.0, route)["phase"], "arrived")

    def test_ping_pong_route_walks_turns_and_returns(self):
        route = OfficePedestrianRoute(
            "person",
            (0.0, 0.0),
            (2.0, 0.0),
            1.0,
            1.0,
            motion_mode="ping_pong",
            turnaround_hold_s=0.5,
        )

        forward = office_pedestrian_state(2.0, route)
        end_turn = office_pedestrian_state(3.25, route)
        reverse = office_pedestrian_state(4.0, route)
        start_turn = office_pedestrian_state(5.75, route)
        next_forward = office_pedestrian_state(6.25, route)

        self.assertEqual(forward["phase"], "walking")
        self.assertEqual(forward["direction"], "forward")
        self.assertEqual(forward["velocity_xy_mps"], (1.0, 0.0))
        self.assertEqual(end_turn["phase"], "turning")
        self.assertAlmostEqual(end_turn["yaw_rad"], math.pi / 2.0)
        self.assertEqual(reverse["direction"], "reverse")
        self.assertEqual(reverse["velocity_xy_mps"], (-1.0, -0.0))
        self.assertEqual(start_turn["phase"], "turning")
        self.assertAlmostEqual(start_turn["yaw_rad"], 1.5 * math.pi)
        self.assertEqual(next_forward["cycle_index"], 1)
        self.assertEqual(next_forward["direction"], "forward")

    def test_office_ping_pong_routes_keep_pairwise_clearance(self):
        root = Path(__file__).resolve().parents[3]
        route_payload = json.loads(
            (
                root
                / ".pipeline/experiments/2026-08-17_office_l0_scan_crowd/office_l0_route_preflight07.json"
            ).read_text()
        )
        routes = routes_from_preflight(
            route_payload,
            motion_mode="ping_pong",
            turnaround_hold_s=0.6,
        )

        result = pairwise_clearance_precheck(routes, 65.0)

        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["minimum_surface_clearance_m"], 0.85)

    def test_background_ping_pong_keeps_crossings_single_pass(self):
        root = Path(__file__).resolve().parents[3]
        route_payload = json.loads(
            (
                root
                / ".pipeline/experiments/2026-08-17_office_l0_scan_crowd/office_l0_route_preflight07.json"
            ).read_text()
        )
        routes = routes_from_preflight(
            route_payload,
            motion_mode="background_ping_pong",
            turnaround_hold_s=0.6,
        )

        self.assertEqual([route.motion_mode for route in routes[:2]], ["single_pass"] * 2)
        self.assertEqual([route.motion_mode for route in routes[2:]], ["ping_pong"] * 6)
        result = pairwise_clearance_precheck(routes, 65.0)
        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["minimum_surface_clearance_m"], 0.64)

    def test_pairwise_precheck_rejects_intersection(self):
        routes = (
            OfficePedestrianRoute("a", (-1.0, 0.0), (1.0, 0.0), 1.0, 0.0),
            OfficePedestrianRoute("b", (0.0, -1.0), (0.0, 1.0), 1.0, 0.0),
        )
        result = pairwise_clearance_precheck(routes, 3.0)
        self.assertFalse(result["passed"])
        self.assertLess(result["minimum_surface_clearance_m"], 0.0)

    def test_crossing_delay_can_be_frozen_from_measured_dry_run(self):
        payload = {
            "path_length_m": 21.0,
            "crossing_pedestrians": [
                {
                    "name": "crossing_1",
                    "start_xy_m": [-2.0, 0.0],
                    "end_xy_m": [2.0, 0.0],
                    "speed_mps": 0.8,
                    "nominal_path_fraction": 0.5,
                    "start_delay_s": 8.0,
                },
                {
                    "name": "crossing_2",
                    "start_xy_m": [-2.0, 4.0],
                    "end_xy_m": [2.0, 4.0],
                    "speed_mps": 0.9,
                    "nominal_path_fraction": 0.75,
                },
            ],
            "background_pedestrians": [
                {
                    "name": f"background_{index}",
                    "start_xy_m": [float(index), 10.0],
                    "end_xy_m": [float(index), 12.0],
                    "speed_mps": 0.6,
                }
                for index in range(1, 7)
            ],
        }

        routes = routes_from_preflight(payload)

        self.assertEqual(routes[0].start_delay_s, 8.0)
        self.assertAlmostEqual(routes[1].start_delay_s, 21.0277777778)
