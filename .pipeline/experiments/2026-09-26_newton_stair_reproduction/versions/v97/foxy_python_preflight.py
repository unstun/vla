"""Exercise original terrain producers and native PCT under Python 3.8/Foxy."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('navigation', 'surface', 'physical', 'pct'))
    parser.add_argument('--recorded', type=Path, default=Path('/task/prepared_inputs'))
    args = parser.parse_args()
    import numpy as np
    assert sys.version_info[:2] == (3, 8) and np.__version__ == '1.24.4'
    result = {'mode': args.mode, 'numpy': np.__version__, 'python': sys.version}
    if args.mode == 'pct':
        from backend_adapter.pct_worker import NativePctPlanner, NativePctConfig
        from backend_adapter.contracts import PlannerRequest
        planner = NativePctPlanner(NativePctConfig(
            Path('/task/pct_workspace/install/pct_planner/lib/python3.8/site-packages'),
            '/task', tomogram_path=str(BASE/'repairs/2026-09-26_generic_occupancy/flat_inputs_v2/flat_floor.pickle')), 0.42)
        route = planner.plan(PlannerRequest('native-test', 'native-goal', (0., 0., 0.),
            (2., 0., 0.), 'world', 'flat', 1, optimize=True))
        assert len(route.waypoints_m) == 10
        assert route.route_id == 'pct:native-goal:bf83960c89de87ded0f6'
        result.update(points=len(route.waypoints_m), route_id=route.route_id)
    else:
        import rclpy
        sys.path.insert(0, str(BASE/'runtime_sources/bridge/lite3_sim_bridge'))
        from pct_sim_clock_publisher import PctSimClockPublisher
        params = ['--ros-args', '-p', 'use_sim_time:=true', '-p',
                  'map_path:='+str(BASE/'inputs/new_building.pickle'), '-p',
                  'elevation_path:='+str(BASE/'inputs/new_building_original_precision.npz')]
        if args.mode == 'surface':
            params += ['-p', 'ground_mode:=surface_evidence', '-p',
                       'dense_surface_path:='+str(BASE/'inputs/new_building_dense_surface.npy')]
        rclpy.init(args=params)
        node = None
        try:
            if args.mode == 'physical':
                from physical_floor_publisher import PhysicalFloorPublisher
                os.environ['V97_PHYSICAL_FLOOR'] = str(args.recorded/'physical_floor.f32')
                node = PhysicalFloorPublisher()
                points = node.points
                original = args.recorded/'physical_floor.f32'
            else:
                node = PctSimClockPublisher()
                points = node._points
                original = args.recorded/(args.mode+'.f32')
            digest = hashlib.sha256(points.astype('<f4').tobytes()).hexdigest()
            assert digest == hashlib.sha256(original.read_bytes()).hexdigest()
            result.update(points=len(points), payload_sha256=digest, original_payload_equal=True)
        finally:
            if node is not None:
                node.destroy_node()
            rclpy.shutdown()
    result['passed'] = True
    print(json.dumps(result))


if __name__ == '__main__':
    main()
