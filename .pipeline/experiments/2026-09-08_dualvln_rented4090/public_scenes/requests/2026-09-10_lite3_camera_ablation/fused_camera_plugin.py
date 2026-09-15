"""habitat-lab plugin: two extra rendered mounts + a task sensor that replaces `rgb` with the fused image.

Import this module BEFORE habitat's config is composed (the run config
public_scenes/configs/habitat_dual_system_fused_cfg.py does so; eval.py executes that
file after importing the evaluator and before Evaluator.init). It registers:

  ConfigStore group habitat/simulator/sim_sensors:
    fused_head_rgb_sensor   -> FusedHeadRGBSensor   (uuid head_rgb)   the stock head camera
    fused_d435_rgb_sensor   -> FusedD435RGBSensor   (uuid d435_rgb)   D435i colour
    fused_d435_depth_sensor -> FusedD435DepthSensor (uuid d435_depth) D435i colour-aligned z-depth
  ConfigStore group habitat/task/lab_sensors:
    fused_rgb_sensor        -> FusedRGBSensor       (uuid rgb)        the fused virtual camera

The virtual camera's pose and intrinsics are those of the ordinary sim `rgb_sensor`, which
stays in the config because the evaluator reads its position, and which therefore also renders
the ideal image the preflight compares against. habitat-lab merges task-sensor observations
over simulator observations in Env.reset/step, so the task sensor's `rgb` is what the agent,
the video writer and every `observations["rgb"]` read receive. No evaluator or model source
is edited. Sim sensor uuids come from `config.uuid` through `_get_uuid` overrides, so this does
not rely on a particular habitat-lab uuid-override behaviour.
"""
import math
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, List

import numpy as np
from gym import spaces
from hydra.core.config_store import ConfigStore

from habitat.config.default_structured_configs import (
    HabitatSimDepthSensorConfig,
    HabitatSimRGBSensorConfig,
    LabSensorConfig,
)
from habitat.core.registry import registry
from habitat.core.simulator import Sensor, SensorTypes
from habitat.sims.habitat_simulator.habitat_simulator import (
    HabitatSimDepthSensor,
    HabitatSimRGBSensor,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fused_camera import Cam, coverage_stats, fuse, head_lut  # noqa: E402

PLUGIN_VERSION = '2026-09-11.2'  # .2: round 6 relaxed the virtual-camera guard from level-only to no yaw/roll


# ----------------------------------------------------------------------------- sim sensors
@dataclass
class FusedHeadRGBSensorConfig(HabitatSimRGBSensorConfig):
    type: str = 'FusedHeadRGBSensor'
    uuid: str = 'head_rgb'


@dataclass
class FusedD435RGBSensorConfig(HabitatSimRGBSensorConfig):
    type: str = 'FusedD435RGBSensor'
    uuid: str = 'd435_rgb'


@dataclass
class FusedD435DepthSensorConfig(HabitatSimDepthSensorConfig):
    type: str = 'FusedD435DepthSensor'
    uuid: str = 'd435_depth'


class _UuidFromConfig:
    def _get_uuid(self, *args: Any, **kwargs: Any) -> str:
        return str(self.config.uuid)


@registry.register_sensor(name='FusedHeadRGBSensor')
class FusedHeadRGBSensor(_UuidFromConfig, HabitatSimRGBSensor):
    pass


@registry.register_sensor(name='FusedD435RGBSensor')
class FusedD435RGBSensor(_UuidFromConfig, HabitatSimRGBSensor):
    pass


@registry.register_sensor(name='FusedD435DepthSensor')
class FusedD435DepthSensor(_UuidFromConfig, HabitatSimDepthSensor):
    pass


# ----------------------------------------------------------------------------- task sensor
@dataclass
class FusedRGBSensorConfig(LabSensorConfig):
    type: str = 'FusedRGBSensor'
    uuid: str = 'rgb'
    virtual_sensor_key: str = 'rgb_sensor'            # sim sensor whose pose/intrinsics define the virtual camera
    head_sensor_key: str = 'fused_head_rgb_sensor'
    d435_rgb_sensor_key: str = 'fused_d435_rgb_sensor'
    d435_depth_sensor_key: str = 'fused_d435_depth_sensor'
    feather_rows: int = 8
    depth_valid_max_m: float = 9.9


def _cam_from_cfg(sc) -> Cam:
    return Cam(int(sc.width), int(sc.height), float(sc.hfov), [float(v) for v in sc.position],
               float(sc.orientation[0]))


@registry.register_sensor(name='FusedRGBSensor')
class FusedRGBSensor(Sensor):
    """Task sensor: fused virtual camera image, uint8 (h, w, 3). The virtual camera may be pitched."""

    def __init__(self, sim, config, *args: Any, **kwargs: Any) -> None:
        self._sim = sim
        self.config = config
        sensors = sim.habitat_config.agents.main_agent.sim_sensors
        vc = sensors[config.virtual_sensor_key]
        hc = sensors[config.head_sensor_key]
        dc = sensors[config.d435_rgb_sensor_key]
        zc = sensors[config.d435_depth_sensor_key]
        # The virtual camera may be pitched about its x axis (round 6 / C9 pitches it 9 deg down to reach the
        # near floor); the fusion maths is pose-general. Yaw and roll stay forbidden: fuse() assumes head
        # coverage lies above D435i coverage, so the seam is a horizontal boundary. Whether the pitched
        # frustum actually stays inside the covered band is gated empirically by the preflight's
        # uncovered-fraction and head-fraction bounds, not asserted here.
        if any(abs(float(v)) > 1e-9 for v in vc.orientation[1:]):
            raise ValueError('FusedRGBSensor: the virtual (rgb_sensor) camera must have no yaw or roll')
        if [float(v) for v in vc.position] != [float(v) for v in hc.position]:
            raise ValueError('FusedRGBSensor: virtual camera and head camera must share the optical centre')
        if (int(dc.width), int(dc.height), float(dc.hfov)) != (int(zc.width), int(zc.height), float(zc.hfov)):
            raise ValueError('FusedRGBSensor: D435i colour and depth must share intrinsics (colour-aligned depth)')
        self.virt, self.head, self.d435 = _cam_from_cfg(vc), _cam_from_cfg(hc), _cam_from_cfg(dc)
        self.head_uuid, self.d435_rgb_uuid, self.d435_depth_uuid = str(hc.uuid), str(dc.uuid), str(zc.uuid)
        self.depth_norm = bool(zc.normalize_depth)
        self.depth_min, self.depth_max = float(zc.min_depth), float(zc.max_depth)
        self.feather_rows = int(config.feather_rows)
        self.depth_valid_max = float(config.depth_valid_max_m)
        self.lut = head_lut(self.virt, self.head)
        self.last_coverage = None
        self.last_ms = None
        super().__init__(config=config)

    def _get_uuid(self, *args: Any, **kwargs: Any) -> str:
        return str(self.config.uuid)

    def _get_sensor_type(self, *args: Any, **kwargs: Any):
        return SensorTypes.COLOR

    def _get_observation_space(self, *args: Any, **kwargs: Any):
        return spaces.Box(low=0, high=255, shape=(self.virt.h, self.virt.w, 3), dtype=np.uint8)

    def fuse_from(self, observations):
        head = np.asarray(observations[self.head_uuid])[..., :3]
        d_rgb = np.asarray(observations[self.d435_rgb_uuid])[..., :3]
        z = np.asarray(observations[self.d435_depth_uuid]).squeeze()
        if self.depth_norm:
            z = z * (self.depth_max - self.depth_min) + self.depth_min
        return fuse(head, d_rgb, z, self.virt, self.head, self.d435,
                    feather_rows=self.feather_rows, depth_valid_max=self.depth_valid_max, lut=self.lut)

    def get_observation(self, observations, *args: Any, episode=None, **kwargs: Any):
        t0 = time.perf_counter()
        img, cov = self.fuse_from(observations)
        self.last_ms = (time.perf_counter() - t0) * 1000.0
        self.last_coverage = coverage_stats(cov)
        return img


def register_configs() -> None:
    # sim-sensor nodes carry no package (habitat-lab 0.2.4 convention: the defaults-list '@' sets it);
    # lab-sensor nodes carry their package like gps_sensor/compass_sensor do.
    cs = ConfigStore.instance()
    cs.store(group='habitat/simulator/sim_sensors', name='fused_head_rgb_sensor', node=FusedHeadRGBSensorConfig)
    cs.store(group='habitat/simulator/sim_sensors', name='fused_d435_rgb_sensor', node=FusedD435RGBSensorConfig)
    cs.store(group='habitat/simulator/sim_sensors', name='fused_d435_depth_sensor', node=FusedD435DepthSensorConfig)
    cs.store(package='habitat.task.lab_sensors.fused_rgb_sensor',
             group='habitat/task/lab_sensors', name='fused_rgb_sensor', node=FusedRGBSensorConfig)


register_configs()
