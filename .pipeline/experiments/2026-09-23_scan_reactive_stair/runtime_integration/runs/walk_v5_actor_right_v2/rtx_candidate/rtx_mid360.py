"""Opt-in RTX geometric snapshot using the pinned Livox CSV ray directions.

This is a geometric adapter, not a manufacturer RTX model. All rays in one
sweep share a pose, matching the existing Warp snapshot contract. No intensity,
weather, return noise, or intra-scan motion distortion is claimed.
"""
from __future__ import annotations

import numpy as np

ANNOTATOR = "IsaacExtractRTXSensorPointCloudNoAccumulator"


class RtxMid360:
    def __init__(self, stage, prim_path, pattern, position=(0.0, 0.0, 1.0),
                 orientation=(1.0, 0.0, 0.0, 0.0)):
        from isaacsim.sensors.rtx import LidarRtx

        self.pattern = pattern
        self.prim = stage.DefinePrim(prim_path, "OmniLidar")
        if not self.prim.ApplyAPI("OmniSensorGenericLidarCoreAPI"):
            raise RuntimeError("RTX core schema unavailable")
        if not self.prim.ApplyAPI("OmniSensorGenericLidarCoreEmitterStateAPI", "s001"):
            raise RuntimeError("RTX emitter-state schema unavailable")
        n = pattern.points_per_scan
        core = {
            "scanType": "SOLID_STATE", "rayType": "IDEALIZED", "rotationDirection": "CW",
            "scanRateBaseHz": 10, "reportRateBaseHz": 10,
            "numberOfEmitters": n, "numberOfChannels": n,
            "nearRangeM": 0.1, "farRangeM": 40.0,
            "maxReturns": 1, "stateResolutionStep": 1,
            "rangeAccuracyM": 0.0, "rangeResolutionM": 0.00001,
            "azimuthErrorMean": 0.0, "azimuthErrorStd": 0.0,
            "elevationErrorMean": 0.0, "elevationErrorStd": 0.0,
            "originErrorMean": (0.0, 0.0, 0.0), "originErrorStd": (0.0, 0.0, 0.0),
            "outputFrameOfReference": "SENSOR",
            "outputMotionCompensationState": "NONCOMPENSATED",
            "auxOutputType": "FULL", "skipDroppingInvalidPoints": True,
            "minReflectance": 0.0, "minReflectionRangeM": 40.0,
            "numLines": 1, "numRaysPerLine": [n],
        }
        for name, value in core.items():
            self._set("omni:sensor:Core:" + name, value)
        self._set("omni:sensor:tickRate", 10.0)
        for name in ("distanceCorrectionM", "focalDistM", "focalSlope", "horOffsetM", "vertOffsetM"):
            self._set("omni:sensor:Core:emitterState:s001:" + name, [0.0] * n)
        self._set("omni:sensor:Core:emitterState:s001:fireTimeNs", [0] * n)
        self._set("omni:sensor:Core:emitterState:s001:reportRateDiv", [0] * n)
        self._set("omni:sensor:Core:emitterState:s001:channelId", list(range(1, n + 1)))
        self.set_window(0)
        self.sensor = LidarRtx(prim_path=prim_path, translation=np.asarray(position),
                              orientation=np.asarray(orientation))
        self.sensor.attach_annotator(ANNOTATOR)

    def _set(self, name, value):
        from pxr import Vt
        attr = self.prim.GetAttribute(name)
        if attr:
            arrays = {"float[]": Vt.FloatArray, "double[]": Vt.DoubleArray,
                      "int[]": Vt.IntArray, "uint[]": Vt.UIntArray,
                      "uint64[]": Vt.UInt64Array}
            array_type = arrays.get(str(attr.GetTypeName()))
            if array_type is not None:
                value = array_type(value)
        if not attr or not attr.Set(value):
            raise RuntimeError("RTX schema attribute rejected: " + name)

    def set_window(self, index):
        directions, window = self.pattern.scan_window(index)
        # RTX's CW spherical azimuth produces -Y for a positive angle. Livox
        # directions use ROS +Y left; the analytic 20k-ray box test checks this.
        azimuth = np.mod(-np.degrees(np.arctan2(directions[:, 1], directions[:, 0])), 360.0)
        elevation = np.degrees(np.arcsin(np.clip(directions[:, 2], -1.0, 1.0)))
        self._set("omni:sensor:Core:emitterState:s001:azimuthDeg", azimuth.tolist())
        self._set("omni:sensor:Core:emitterState:s001:elevationDeg", elevation.tolist())
        self.window = window
        return directions

    def points(self):
        raw = self.sensor.get_annotators()[ANNOTATOR].get_data()
        points = np.asarray(raw["data"], dtype=np.float32).reshape(-1, 3)
        distance = np.linalg.norm(points, axis=1)
        return points[np.isfinite(points).all(axis=1) & (distance >= 0.1) & (distance <= 40.0)].copy(), raw


def release_scene(app, sim, sensors=(), annotators=(), render_products=()):
    """Terminal cleanup for the pinned IsaacLab STOP callback implementation."""
    if sim is not None:
        sim._disable_app_control_on_stop_handle = True
        sim.stop()
    # Detach every annotator before destroying any render product. The RGB
    # graph can otherwise retain shared nodes removed by the LiDAR product.
    for annotator in annotators:
        annotator.detach()
    for sensor in sensors:
        sensor.detach_all_annotators()
        sensor.detach_all_writers()
        sensor._acquisition_callback = None
        sensor._stage_open_callback = None
        sensor._timer_reset_callback = None
    for product in render_products:
        product.destroy()
    for sensor in sensors:
        if sensor._render_product is not None:
            sensor._render_product.destroy()
            sensor._render_product = None
    for _ in range(3):
        app.update()
    if sim is not None:
        sim.clear_instance()
