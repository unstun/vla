# habitat-lab v0.2.4 sensor / config API excerpts (fetched 2026-09-11)

Purpose: primary-source basis for the round-5 fused-camera plugin
(`.pipeline/experiments/2026-09-08_dualvln_rented4090/public_scenes/requests/2026-09-10_lite3_camera_ablation/fused_camera_plugin.py`).
Files are verbatim copies from the `v0.2.4` tag of https://github.com/facebookresearch/habitat-lab
(raw URLs `https://raw.githubusercontent.com/facebookresearch/habitat-lab/v0.2.4/habitat-lab/habitat/<path>`), MIT licence,
fetched by a web subagent; the rented4090 official env installs the same version as an editable checkout
(`official_r2r/src/habitat-lab-024`). Label: surveyed (not re-diffed against the remote checkout yet).

Facts relied on (file:line in the copies):
- core/simulator.py: `Sensor.__init__` takes `self.uuid` from `config.uuid` when present; `RGBSensor._get_uuid` = "rgb", `DepthSensor` = "depth".
- config/default_structured_configs.py: `LabSensorConfig` has only `type`; `HabitatSimRGBSensorConfig` / `HabitatSimDepthSensorConfig`
  carry no `uuid`; `HeadRGBSensorConfig` etc. add `uuid`; sim-sensor `cs.store` calls carry no `package=`, lab-sensor calls carry
  `package="habitat.task.lab_sensors.<name>"`.
- sims/habitat_simulator/habitat_simulator.py: sensors instantiated by `registry.get_sensor(cfg.type)(cfg)`; spec uuid set from
  `sensor.uuid`; depth `get_observation` clips to [min,max] and normalises only if `normalize_depth`.
- core/embodied_task.py: lab sensors built with `sim=, config=, dataset=, task=`; `reset`/`step` do
  `observations.update(self.sensor_suite.get_observations(...))` -> a task sensor with uuid `rgb` overrides the sim `rgb`.
- core/env.py: observation_space = sim spaces then task spaces.
- config/default.py: `get_config` composes through the global Hydra ConfigStore, so nodes stored before the call are visible.
