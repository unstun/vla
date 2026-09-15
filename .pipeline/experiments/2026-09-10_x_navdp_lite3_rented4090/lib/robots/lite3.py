"""Physical Lite3 backend using the pinned v12 model_149999 ONNX policy."""

from __future__ import annotations

import hashlib
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np

from ..model import PHYSICS_DT, SPAWN, load_scene_xml
from .base import RenderCamera, RobotState, Twist2D

POLICY_SHA256 = "7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b"
JOINT_NAMES = tuple(f"{leg}_{joint}_joint" for leg in ("FL", "FR", "HL", "HR")
                    for joint in ("HipX", "HipY", "Knee"))
Q0 = np.tile(np.array([0.0, -0.8, 1.6], dtype=np.float32), 4)
EFFORT = np.tile(np.array([24.0, 24.0, 36.0], dtype=np.float32), 4)
SPEED = np.tile(np.array([26.2, 26.2, 17.3], dtype=np.float32), 4)
FEATURE_DIMS = (3, 3, 3, 12, 12, 12)
SIM_DT = 0.001
POLICY_DT = 0.02
PREFIX = "lite3/"
CAMERA_NAME = PREFIX + "robot_rgb"


def rotation_matrix(quaternion: np.ndarray) -> np.ndarray:
    """Body-to-world rotation for a MuJoCo wxyz quaternion."""
    q = np.asarray(quaternion, dtype=np.float64)
    if q.shape != (4,) or not np.isfinite(q).all() or np.linalg.norm(q) < 1e-8:
        raise ValueError("Invalid Lite3 quaternion")
    q = q / np.linalg.norm(q)
    w, x, y, z = q
    return np.array([
        [1 - 2 * (y*y + z*z), 2 * (x*y - z*w), 2 * (x*z + y*w)],
        [2 * (x*y + z*w), 1 - 2 * (x*x + z*z), 2 * (y*z - x*w)],
        [2 * (x*z - y*w), 2 * (y*z + x*w), 1 - 2 * (x*x + y*y)],
    ])


class History:
    def __init__(self) -> None:
        self.values: np.ndarray | None = None

    def reset(self) -> None:
        self.values = None

    def push(self, observation: np.ndarray) -> np.ndarray:
        frame = np.asarray(observation, dtype=np.float32)
        if frame.shape != (45,) or not np.isfinite(frame).all():
            raise ValueError("Lite3 observation must be finite shape (45,)")
        if self.values is None:
            self.values = np.repeat(frame[None, :], 10, axis=0)
        else:
            self.values[:-1] = self.values[1:]
            self.values[-1] = frame
        terms = np.split(self.values, np.cumsum(FEATURE_DIMS)[:-1], axis=1)
        return np.concatenate([term.reshape(-1) for term in terms])[None, :]


def build_model(robot_source: Path, scene_source: Path | None = None) -> mujoco.MjModel:
    scene = mujoco.MjSpec.from_string(ET.tostring(load_scene_xml(scene_source), encoding="unicode"))
    robot = mujoco.MjSpec.from_file(str(robot_source.resolve()))
    # ProcTHOR structural floors use contype=8, conaffinity=15. The vendor
    # robot's 0/1 masks cannot touch them. Reserve bit 2 for robot colliders;
    # excluding that bit from their affinity preserves disabled self-contact.
    for geom in robot.geoms:
        if geom.conaffinity:
            geom.contype = 2
            geom.conaffinity = 13
    torso = robot.body("base_link")
    if torso is None:
        raise ValueError("Lite3 MJCF must contain base_link")
    torso.pos = [SPAWN[0], SPAWN[1], 0.35]
    torso.add_freejoint(name="base_joint")
    camera = torso.add_camera(name="robot_rgb", pos=[0.24, 0.0, 0.08])
    camera.quat = [-0.5, -0.5, 0.5, 0.5]
    camera.fovy = 79.865
    chase = torso.add_camera(name="robot_chase", pos=[-1.3, 0.0, 0.70])
    # Camera x points right (-body Y); camera y points up and slightly forward.
    angle = math.atan2(0.38, 0.925)
    qbase = np.array([-0.5, -0.5, 0.5, 0.5])
    qtilt = np.array([math.cos(angle/2), -math.sin(angle/2), 0, 0])
    quat = np.empty(4)
    mujoco.mju_mulQuat(quat, qbase, qtilt)
    chase.quat = quat
    chase.fovy = 65
    scene.attach(robot, prefix=PREFIX, frame=scene.worldbody.add_frame())
    model = scene.compile()
    model.opt.timestep = SIM_DT
    if model.nu != 12:
        raise ValueError(f"Lite3 requires exactly 12 actuators; got {model.nu}")
    return model


class Lite3Backend:
    name = "Lite3 (model_149999)"
    camera_name = CAMERA_NAME

    def __init__(self, robot_model: Path, walking_policy: Path, *, session=None,
                 scene_source: Path | None = None) -> None:
        if hashlib.sha256(walking_policy.read_bytes()).hexdigest() != POLICY_SHA256:
            raise ValueError("Lite3 walking-policy SHA-256 mismatch")
        if session is None:
            import onnxruntime as ort

            options = ort.SessionOptions()
            options.intra_op_num_threads = 1
            options.inter_op_num_threads = 1
            session = ort.InferenceSession(str(walking_policy), sess_options=options,
                                           providers=["CPUExecutionProvider"])
        self.session = session
        inp, out = self.session.get_inputs()[0], self.session.get_outputs()[0]
        if inp.shape != [1, 450] or out.shape != [1, 12] or inp.type != "tensor(float)":
            raise ValueError("Lite3 policy requires float32 [1,450] -> [1,12]")
        self.input_name, self.output_name = inp.name, out.name
        self.model = build_model(robot_model, scene_source)
        self.data = mujoco.MjData(self.model)
        self.scene_metadata = ({"id": f"lite3-capability-{scene_source.stem}",
                                "name": f"Controlled {scene_source.stem} arena",
                                "dataset": "task-owned arena with pinned ProcTHOR trashcan"}
                               if scene_source is not None else None)
        self.robot_geoms = {g for g in range(self.model.ngeom)
                            if (mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_GEOM, g) or "").startswith(PREFIX)}
        self.obstacle_geoms = {g for g in range(self.model.ngeom)
                               if mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_GEOM, g) == "test_obstacle"}
        self.boundary_geoms = {g for g in range(self.model.ngeom)
                               if (mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_GEOM, g) or "").startswith("test_wall_")}
        self._contact_force = np.zeros(6)
        self.base_joint = self.model.joint(PREFIX + "base_joint").id
        self.base_qpos = int(self.model.jnt_qposadr[self.base_joint])
        self.base_dof = int(self.model.jnt_dofadr[self.base_joint])
        joints = [self.model.joint(PREFIX + name).id for name in JOINT_NAMES]
        self.joint_qpos = self.model.jnt_qposadr[joints]
        self.joint_dof = self.model.jnt_dofadr[joints]
        self.actuators = np.array([self.model.actuator(PREFIX + name + "_ctrl").id
                                  for name in JOINT_NAMES])
        if not np.array_equal(self.model.actuator_trnid[self.actuators, 0], joints):
            raise ValueError("Lite3 actuator/joint mapping mismatch")
        self.history = History()
        self.reset()

    def reset(self) -> None:
        mujoco.mj_resetData(self.model, self.data)
        self.history.reset()
        self.last_action = np.zeros(12, dtype=np.float32)
        self.target = Q0.copy()
        self.policy_command = np.zeros(3, dtype=np.float32)
        self.steps = 0
        self.inferences = 0
        self.last_observation = np.zeros(45, dtype=np.float32)
        self.last_torque = np.zeros(12, dtype=np.float32)
        self.obstacle_contact_steps = 0
        self.boundary_contact_steps = 0
        self.maximum_obstacle_force = 0.0
        self.minimum_obstacle_contact_distance = None
        self.first_obstacle_contact_sim_time = None
        self.data.qpos[self.base_qpos:self.base_qpos + 3] = [SPAWN[0], SPAWN[1], 0.35]
        self.data.qpos[self.base_qpos + 3:self.base_qpos + 7] = [1, 0, 0, 0]
        self.data.qpos[self.joint_qpos] = Q0
        mujoco.mj_forward(self.model, self.data)

    def _infer(self, command: Twist2D) -> None:
        cmd = np.asarray(command, dtype=np.float32)
        if cmd.shape != (2,) or not np.isfinite(cmd).all():
            raise ValueError("Lite3 velocity command must be finite shape (2,)")
        self.policy_command = np.array([np.clip(cmd[0], -1, 1), 0,
                                        np.clip(cmd[1], -2, 2)], dtype=np.float32)
        quaternion = self.data.qpos[self.base_qpos + 3:self.base_qpos + 7]
        rotation = rotation_matrix(quaternion)
        # The named gyro sensor is already expressed in the torso/IMU frame.
        ang = self.data.sensor(PREFIX + "imu_gyro").data
        observation = np.concatenate([
            np.clip(ang, -100, 100) * 0.25,
            rotation.T @ np.array([0., 0., -1.]),
            self.policy_command,
            np.clip(self.data.qpos[self.joint_qpos] - Q0, -100, 100),
            np.clip(self.data.qvel[self.joint_dof], -100, 100) * 0.05,
            np.clip(self.last_action, -100, 100),
        ]).astype(np.float32)
        self.last_observation = observation.copy()
        history = self.history.push(observation)
        action = np.asarray(self.session.run([self.output_name], {self.input_name: history})[0])
        if action.shape != (1, 12) or not np.isfinite(action).all():
            raise ValueError("Lite3 returned invalid actions")
        self.last_action = action[0].astype(np.float32)
        self.target = Q0 + 0.25 * self.last_action
        self.inferences += 1

    def step(self, command: Twist2D) -> None:
        substeps = round(PHYSICS_DT / SIM_DT)
        if abs(substeps * SIM_DT - PHYSICS_DT) > 1e-9:
            raise ValueError("Demo period must be an integer multiple of Lite3 physics dt")
        for _ in range(substeps):
            if self.steps % round(POLICY_DT / SIM_DT) == 0:
                self._infer(command)
            position = self.data.qpos[self.joint_qpos].astype(np.float32)
            velocity = self.data.qvel[self.joint_dof].astype(np.float32)
            requested = 20.0 * (self.target - position) - 0.5 * velocity
            high = np.clip(EFFORT * (1.0 - velocity / SPEED), 0.0, EFFORT)
            low = np.clip(EFFORT * (-1.0 - velocity / SPEED), -EFFORT, 0.0)
            self.last_torque = np.clip(requested, low, high)
            self.data.ctrl[self.actuators] = self.last_torque
            mujoco.mj_step(self.model, self.data)
            self._observe_contacts()
            self.steps += 1
            if not np.isfinite(self.data.qpos).all() or not np.isfinite(self.data.qvel).all():
                raise RuntimeError("Lite3 physics became nonfinite")

    def _observe_contacts(self) -> None:
        """Accumulate obstacle contacts every 1 ms, including between camera samples."""
        obstacle_hit = False
        boundary_hit = False
        for index in range(self.data.ncon):
            contact = self.data.contact[index]
            first, second = int(contact.geom1), int(contact.geom2)
            if first in self.robot_geoms:
                environment = second
            elif second in self.robot_geoms:
                environment = first
            else:
                continue
            if environment not in self.obstacle_geoms | self.boundary_geoms:
                continue
            if contact.efc_address < 0:
                continue
            mujoco.mj_contactForce(self.model, self.data, index, self._contact_force)
            force = abs(float(self._contact_force[0]))
            if contact.dist > 0 and force <= 0.1:
                continue
            if environment in self.obstacle_geoms:
                obstacle_hit = True
                self.maximum_obstacle_force = max(self.maximum_obstacle_force, force)
                self.minimum_obstacle_contact_distance = min(
                    float(contact.dist), self.minimum_obstacle_contact_distance
                    if self.minimum_obstacle_contact_distance is not None else float(contact.dist))
                if self.first_obstacle_contact_sim_time is None:
                    self.first_obstacle_contact_sim_time = float(self.data.time)
            else:
                boundary_hit = True
        self.obstacle_contact_steps += int(obstacle_hit)
        self.boundary_contact_steps += int(boundary_hit)

    def state(self) -> RobotState:
        x, y, z = self.data.qpos[self.base_qpos:self.base_qpos + 3]
        quaternion = self.data.qpos[self.base_qpos + 3:self.base_qpos + 7]
        rotation = rotation_matrix(quaternion)
        yaw = math.atan2(rotation[1, 0], rotation[0, 0])
        velocity = rotation.T @ self.data.qvel[self.base_dof:self.base_dof + 3]
        angular_world = rotation @ self.data.sensor(PREFIX + "imu_gyro").data
        tilt = math.acos(float(np.clip(rotation[2, 2], -1, 1)))
        return RobotState(
            (float(x), float(y), float(z), yaw),
            (float(velocity[0]), float(angular_world[2])),
            {"walking_policy": "model_149999", "walking_precision": "FP32 ONNX CPU",
             "policy_command": self.policy_command.tolist(), "tilt_rad": tilt,
             "policy_inferences": self.inferences, "contact_count": int(self.data.ncon),
             "obstacle_contact_steps": self.obstacle_contact_steps,
             "boundary_contact_steps": self.boundary_contact_steps,
             "maximum_obstacle_force_N": self.maximum_obstacle_force,
             "minimum_obstacle_contact_distance_m": self.minimum_obstacle_contact_distance,
             "first_obstacle_contact_sim_time": self.first_obstacle_contact_sim_time},
        )

    def third_person_camera(self, _camera: mujoco.MjvCamera) -> RenderCamera:
        return PREFIX + "robot_chase"
