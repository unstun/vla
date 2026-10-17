"""Coverage-aware foreground wrapper; current association core is unchanged."""
from __future__ import annotations

from moving_cluster_core import MovingClusterTracker, TrackerParameters
from static_background import MINIMUM_BACKGROUND_MATCH_FRACTION


class StaticForegroundTracker(MovingClusterTracker):
    SOURCE_ID = "sensor_lidar_static_background_cluster_v3"

    def __init__(self, background, parameters: TrackerParameters = TrackerParameters()):
        super().__init__(parameters)
        self.background = background
        self.last_background_metrics = None

    def process(self, cloud, pose, terrain, now_ns):
        self.last_background_metrics = None
        if self.background is None:
            return self._invalid(cloud, terrain, "missing_static_background")
        if pose is None or terrain is None:
            return self._invalid(cloud, terrain, "missing_pose_or_terrain")
        try:
            selected = self.background.select(cloud, pose, self.p)
            unknown = sum(terrain.ground_below(*point) is None for point in selected.world_points)
        except (ValueError, OverflowError, ZeroDivisionError):
            return self._invalid(cloud, terrain, "invalid_foreground_input")
        self.last_background_metrics = {
            "source_id": selected.background_source_id,
            "input_points": selected.input_points,
            "in_range_points": selected.in_range_points,
            "foreground_points": len(selected.cloud.points),
            "matched_fraction": selected.matched_fraction,
            "unknown_foreground_ground": unknown,
        }
        if selected.matched_fraction < MINIMUM_BACKGROUND_MATCH_FRACTION:
            return self._invalid(cloud, terrain, "static_background_alignment_missing")
        if unknown:
            return self._invalid(cloud, terrain, "foreground_ground_coverage_missing")
        # Base processing retains exact-stamp/frame, freshness, terrain validity,
        # non-monotonic input, unresolved candidate and confirmed-track-loss gates.
        # It consumes only current measured points; no human truth or prediction.
        return super().process(selected.cloud, pose, terrain, now_ns)
