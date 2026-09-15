"""Immutable upstream pins and Lite3 control constants used by the evaluator."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourcePin:
    name: str
    url: str
    commit: str


ROBOGAUGE = SourcePin(
    name="wty-yy/RoboGauge",
    url="https://github.com/wty-yy/RoboGauge.git",
    commit="30643dfed8cf9cf0f9919ebe8c369fd9004087ca",
)
GO2_RL_GYM = SourcePin(
    name="wty-yy/go2_rl_gym",
    url="https://github.com/wty-yy/go2_rl_gym.git",
    commit="30e74dc507bec7a642a8c98be26081f2c6f0822d",
)
DEEP_ROBOTICS_MODEL = SourcePin(
    name="DeepRoboticsLab/deep_robotics_model",
    url="https://github.com/DeepRoboticsLab/deep_robotics_model.git",
    commit="1f46ba1f86c72ddafd3d79e1e9725805c202bf2b",
)

OFFICIAL_LITE3_MJCF_SHA256 = "512a93c353e111c4bf595eba429344599c4b0b617bb917c281d1e7cd648b2aed"
OFFICIAL_LITE3_MESH_SHA256 = {
    "hip.STL": "3386fa94992dbfc4d3e06c6d9fb110e2c4abd87f94c3ac766fdcce85c43341f3",
    "shank.STL": "5410bae3b9b1e9fbc30343041450a80fc609806c2a83418bd2288b0720aec098",
    "thigh.STL": "f29ea97407a9a30cb4549206d080848350d8b455bf4b9a63441241cdacab1719",
    "torso.STL": "6f3f5fc4b9985db56d741ac1b6b93e11d9fb283eb128f8800ad9603772bbcda2",
}

JOINT_NAMES = (
    "FL_HipX_joint",
    "FL_HipY_joint",
    "FL_Knee_joint",
    "FR_HipX_joint",
    "FR_HipY_joint",
    "FR_Knee_joint",
    "HL_HipX_joint",
    "HL_HipY_joint",
    "HL_Knee_joint",
    "HR_HipX_joint",
    "HR_HipY_joint",
    "HR_Knee_joint",
)
ACTUATOR_NAMES = tuple(f"{name}_ctrl" for name in JOINT_NAMES)
FOOT_GEOM_NAMES = (
    "FL_FOOT_collision",
    "FR_FOOT_collision",
    "HL_FOOT_collision",
    "HR_FOOT_collision",
)

DEFAULT_DOF_POS = (0.0, -0.8, 1.6) * 4
P_GAINS = (20.0,) * 12
D_GAINS = (0.5,) * 12
ACTION_SCALE = (0.25,) * 12
EFFORT_LIMITS = (24.0, 24.0, 36.0) * 4
VELOCITY_LIMITS = (26.2, 26.2, 17.3) * 4
SPAWN_HEIGHT_M = 0.35
SIMULATION_DT_S = 0.002
CONTROL_DT_S = 0.02

SINGLE_OBSERVATION_DIM = 45
HISTORY_LENGTH = 10
ACTOR_OBSERVATION_DIM = SINGLE_OBSERVATION_DIM * HISTORY_LENGTH
ACTION_DIM = 12
