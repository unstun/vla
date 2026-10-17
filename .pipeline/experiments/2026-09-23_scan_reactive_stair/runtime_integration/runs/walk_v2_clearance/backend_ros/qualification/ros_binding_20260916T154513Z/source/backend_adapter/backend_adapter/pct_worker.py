"""Native PCT worker/server entrypoint.

Run this inside the existing PCT/Humble image with the frozen PCT modules and map
mounted.  The worker handles one JSON-line request per TCP connection and exits
only when the process is stopped by the launcher.  It never falls back to a
hardcoded route.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import socketserver
import sys
import threading
import traceback
from dataclasses import dataclass
from typing import Any, List, Mapping, Optional, Tuple

from .contracts import ContractError, NativeRoute, PlannerRequest, decode_json_line, encode_json_line
from .pct_ipc import error_response, make_route_id, ok_response, rejected_response


@dataclass(frozen=True)
class NativePctConfig:
    pct_source_root: pathlib.Path
    rsg_root: str
    tomo_file: str = ""
    tomogram_path: str = ""


class NativePctPlanner:
    def __init__(self, config: NativePctConfig, reference_height_m: float = 0.35) -> None:
        self.config = config
        self.reference_height_m = float(reference_height_m)
        self._lock = threading.Lock()
        source_root = config.pct_source_root.expanduser().resolve()
        if not source_root.exists():
            raise RuntimeError("pct_source_root_missing:%s" % source_root)
        if str(source_root) not in sys.path:
            sys.path.insert(0, str(source_root))
        try:
            from pct_planner.config import Config  # type: ignore
            from pct_planner.planner_wrapper import TomogramPlanner  # type: ignore
        except Exception as exc:
            raise RuntimeError("pct_native_import_failed") from exc
        self._planner = TomogramPlanner(Config(), config.rsg_root)
        try:
            self._planner.loadTomogram(tomo_file=config.tomo_file, tomogram_path=config.tomogram_path)
        except Exception as exc:
            raise RuntimeError("pct_tomogram_load_failed") from exc

    def plan(self, request: PlannerRequest) -> NativeRoute:
        if not request.optimize:
            raise ValueError("pct_worker_requires_optimize_true_for_body_reference_z")
        with self._lock:
            try:
                if hasattr(self._planner.planner, "set_reference_height"):
                    self._planner.planner.set_reference_height(self.reference_height_m)
                raw = self._planner.plan(
                    request.start_xyz_m,
                    request.target_xyz_m,
                    start_layer=request.start_layer,
                    end_layer=request.target_layer,
                    optimize=True,
                )
                heights = self._native_optimizer_heights()
            except Exception as exc:
                raise RuntimeError("pct_native_plan_failed") from exc
        if raw is None:
            raise ValueError("pct_no_route")
        waypoints = _coerce_waypoints(raw)
        waypoints = _replace_display_z_with_native_heights(waypoints, heights)
        route_id = make_route_id(request, waypoints)
        return NativeRoute(
            route_id=route_id,
            goal_id=request.goal_id,
            frame_id=request.frame_id,
            map_epoch=request.map_epoch,
            map_revision=request.map_revision,
            waypoints_m=waypoints,
        )


    def _native_optimizer_heights(self):
        optimizer = (
            self._planner.planner.get_trajectory_optimizer()
            if not self._planner.use_quintic
            else self._planner.planner.get_trajectory_optimizer_wnoj()
        )
        heights = optimizer.get_heights()
        if hasattr(heights, "tolist"):
            heights = heights.tolist()
        return [float(v[0] if isinstance(v, (list, tuple)) else v) for v in heights]


def _coerce_waypoints(raw: Any) -> Tuple[Tuple[float, float, float], ...]:
    # Accept numpy arrays without importing numpy in the Foxy adapter path.
    if hasattr(raw, "tolist"):
        raw = raw.tolist()
    if not isinstance(raw, list) or len(raw) < 2:
        raise ContractError("invalid_pct_waypoints")
    points = []
    for row in raw:
        if not isinstance(row, (list, tuple)) or len(row) < 3:
            raise ContractError("invalid_pct_waypoint")
        points.append((float(row[0]), float(row[1]), float(row[2])))
    return tuple(points)


def _replace_display_z_with_native_heights(waypoints: Tuple[Tuple[float, float, float], ...], heights: Any) -> Tuple[Tuple[float, float, float], ...]:
    if len(waypoints) != len(heights):
        raise ContractError("pct_height_count_mismatch")
    converted = []
    for point, height in zip(waypoints, heights):
        height_f = float(height)
        display_delta = float(point[2]) - height_f
        if abs(display_delta - 0.5) > 1e-3:
            raise ContractError("pct_display_height_delta_mismatch")
        converted.append((float(point[0]), float(point[1]), height_f))
    return tuple(converted)


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        planner = self.server.planner  # type: ignore[attr-defined]
        raw = self.rfile.readline(4 * 1024 * 1024)
        try:
            payload = decode_json_line(raw)
            request = PlannerRequest.from_mapping(payload)
            route = planner.plan(request)
            response = ok_response(route)
        except ValueError as exc:
            response = rejected_response(str(exc))
        except Exception as exc:
            response = error_response(str(exc))
        self.wfile.write(encode_json_line(response))


class PctWorkerServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: Tuple[str, int], planner: NativePctPlanner) -> None:
        super().__init__(address, _Handler)
        self.planner = planner


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="P2B native PCT JSON-line worker")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=47631)
    parser.add_argument("--pct-source-root", required=True, help="Path containing pct_planner package")
    parser.add_argument("--rsg-root", required=True, help="PCT rsg_root used by TomogramPlanner")
    parser.add_argument("--tomo-file", default="")
    parser.add_argument("--tomogram-path", default="")
    parser.add_argument("--reference-height-m", type=float, default=0.35)
    args = parser.parse_args(argv)
    planner = NativePctPlanner(NativePctConfig(
        pct_source_root=pathlib.Path(args.pct_source_root),
        rsg_root=args.rsg_root,
        tomo_file=args.tomo_file,
        tomogram_path=args.tomogram_path,
    ), reference_height_m=args.reference_height_m)
    server = PctWorkerServer((args.host, args.port), planner)
    print(json.dumps({"schema": "p2b_pct_worker_ready_v1", "host": args.host, "port": args.port}, sort_keys=True), flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
