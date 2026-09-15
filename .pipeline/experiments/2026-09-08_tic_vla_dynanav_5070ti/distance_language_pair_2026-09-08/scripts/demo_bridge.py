"""Simulation-thread adapter plus loopback HTTP transport for the hospital demo."""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np

from protocol import CommandLatch, INSTRUCTION, body_to_world, project_points


class DemoBridge:
    def __init__(self, behavior):
        self.latch = CommandLatch()
        self.lock = threading.Lock()
        self.state = {"ready": False}
        self.images = {}
        self.path = []
        self.plan = []
        self.plan_frame = None
        from distance_probe import DistanceMeter
        self.distance_meter = DistanceMeter()
        self.sequence = 0
        self.last_publish = -1
        self.started = time.monotonic()
        self.directory = Path(os.environ["TICVLA_DEMO_RUN"])
        (self.directory / "frames").mkdir(parents=True, exist_ok=True)
        self.trace = (self.directory / "telemetry.jsonl").open("a", buffering=1)
        self.events = (self.directory / "commands.jsonl").open("a", buffering=1)
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self, status, data, mime="application/json"):
                if not isinstance(data, bytes):
                    data = json.dumps(data, ensure_ascii=False).encode()
                self.send_response(status)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_GET(self):
                name = self.path.split("?")[0]
                with bridge.lock:
                    if name == "/status":
                        data = dict(bridge.state, **bridge.latch.snapshot())
                        data["server_time_unix"] = time.time()
                        return self.respond(200, data)
                    data = bridge.images.get(name)
                if data:
                    self.respond(200, data, "image/jpeg")
                else:
                    self.respond(404, {"error": "No rendered frame yet"})

            def do_POST(self):
                if self.path != "/command":
                    return self.respond(404, {"error": "Unknown endpoint"})
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 1 <= length <= 2048:
                        raise ValueError("Invalid request size")
                    command = bridge.latch.submit(json.loads(self.rfile.read(length)))
                    with bridge.lock:
                        bridge.events.write(json.dumps(dict(command, event="received", time_unix=time.time())) + "\n")
                    self.respond(200, command)
                except (ValueError, TypeError, AttributeError) as error:
                    self.respond(400, {"error": str(error)})

        self.server = None
        self.offline_pending = os.environ.get("TICVLA_DEMO_OFFLINE") == "1"
        self.instruction = os.environ["TICVLA_DEMO_INSTRUCTION"] if self.offline_pending else INSTRUCTION
        if os.environ.get("TICVLA_DEMO_OFFLINE") == "1":
            print("TICVLA_OFFLINE_WAITING_FOR_CAMERA", flush=True)
        else:
            self.server = ThreadingHTTPServer(("127.0.0.1", 18766), Handler)
            threading.Thread(target=self.server.serve_forever, daemon=True).start()
        print("TICVLA_DEMO_BRIDGE_READY", self.directory, flush=True)

    def before_update(self, behavior):
        # Wait for advancing benchmark frames and two rendered cameras. Empty
        # startup buffers must not seed the first semantic-generation cache.
        if self.offline_pending and int(behavior._frame_count) >= 120:
            front, third = behavior._camera_image_front, behavior._camera_image_tp
            if front is not None and third is not None and front.size and third.size:
                self.latch.submit({"id": "offline-goal", "text": self.instruction})
                self.offline_pending = False
        command = self.latch.take()
        if command:
            behavior._cmd_v = behavior._cmd_w = 0.0
            behavior._current_action = np.zeros(2, dtype=np.float32)
            behavior._wheeled_robot.apply_wheel_actions(behavior._diff.forward(command=np.zeros(2)))
            self.plan = []
            if command["action"] != "stop":
                # Called only by the simulation thread, before any new prediction.
                behavior._ticvla_model.reset_episode_state()
                if command["id"] == "offline-goal" and "TICVLA_INFERENCE_SEED" in os.environ:
                    import random
                    import torch
                    seed = int(os.environ["TICVLA_INFERENCE_SEED"])
                    random.seed(seed)
                    np.random.seed(seed)
                    torch.manual_seed(seed)
                    torch.cuda.manual_seed_all(seed)
                    print("TICVLA_INFERENCE_SEED", seed, flush=True)
                if command["action"] == "goal":
                    self.instruction = command["instruction"]
                behavior._instruction = self.instruction
                behavior._first_inference_complete = False
                behavior._is_backing_up = False
                behavior._backup_start_frame = None
                behavior._waiting_for_inference_after_backup = False
                behavior._last_movement_position = None
                behavior._last_movement_frame = None
                behavior._vlm_generation_start_frames.clear()
                behavior._vlm_generation_start_positions.clear()
                behavior._vlm_generation_start_quaternions.clear()
                behavior._image_history.clear()
                behavior._delta_1s_sampled_1s.clear()
                behavior._delta_1s_sampled_1s.append((int(behavior._frame_count), [0.0, 0.0, 0.0]))
                behavior._prev_position_for_offset = None
                if hasattr(behavior, "_yaw_err_filt"):
                    del behavior._yaw_err_filt
            if command["action"] == "goal":
                from omni.timeline import get_timeline_interface
                self.distance_meter.start(behavior._robot_position.tolist(), behavior._robot_quaternion.tolist(),
                                          get_timeline_interface().get_current_time(), behavior._frame_count)
                print("TICVLA_METRIC_STOP_PROBE goal_stop=False automatic_backup=False distance_control=False", flush=True)
            self.latch.acknowledge(command)
            with self.lock:
                self.events.write(json.dumps(dict(command, event="applied", time_unix=time.time(),
                                                 frame=int(behavior._frame_count))) + "\n")
        if self.latch.is_held():
            behavior._cmd_v = behavior._cmd_w = 0.0
            behavior._current_action = np.zeros(2, dtype=np.float32)
            behavior._wheeled_robot.apply_wheel_actions(behavior._diff.forward(command=np.zeros(2)))
            return True
        return False

    def capture_plan(self, waypoints, robot_pose, frame):
        if self.latch.is_held():
            return
        if np.shape(waypoints) != (30, 2) or not np.isfinite(waypoints).all():
            raise ValueError("Invalid demo trajectory")
        self.plan = body_to_world(waypoints.tolist(), robot_pose["position"], robot_pose["quaternion"])
        self.plan_frame = int(frame)

    def guard_command(self, v, w):
        return (0.0, 0.0) if self.latch.is_held() else (v, w)

    @staticmethod
    def draw_line(image, points, matrix, color, thickness):
        height, width = image.shape[:2]
        pixels = project_points(points, matrix, width, height)
        for a, b in zip(pixels, pixels[1:]):
            if a is not None and b is not None:
                visible, start, end = cv2.clipLine((0, 0, width, height), a, b)
                if visible:
                    cv2.line(image, start, end, color, thickness, cv2.LINE_AA)

    def publish(self, behavior, v=0.0, w=0.0):
        frame = int(behavior._frame_count)
        if frame % 3 or frame == self.last_publish:
            return
        self.last_publish = frame
        from pxr import UsdGeom
        import omni.usd

        position = behavior._robot_position.tolist()
        if not self.path or np.linalg.norm(np.asarray(position[:2]) - self.path[-1][:2]) > 0.025:
            self.path.append([position[0], position[1], 0.065])
        stage = omni.usd.get_context().get_stage()
        camera = UsdGeom.Camera(stage.GetPrimAtPath(behavior._camera_tp_prim_path)).GetCamera()
        matrix = np.array(camera.frustum.ComputeViewMatrix() * camera.frustum.ComputeProjectionMatrix()).tolist()
        plan = [] if self.latch.is_held() else self.plan
        state = {"ready": True, "time_unix": time.time(), "sequence": self.sequence,
                 "inference_seed": int(os.environ["TICVLA_INFERENCE_SEED"]) if "TICVLA_INFERENCE_SEED" in os.environ else None,
                 "camera_view": os.environ.get("TICVLA_DEMO_VIEW", "third_person"),
                 "run_id": self.directory.name, "frame": frame,
                 "elapsed_wall_seconds": time.monotonic() - self.started,
                 "position": position, "planned_world": plan, "actual_world": self.path,
                 "plan_frame": self.plan_frame, "world_to_clip": matrix,
                 "v": float(v), "w": float(w), "instruction": behavior._instruction,
                 **self.latch.snapshot()}
        from omni.timeline import get_timeline_interface
        state["distance_probe"] = self.distance_meter.sample(
            position, behavior._robot_velocity.tolist(), behavior._robot_yaw_speed,
            behavior._current_action.tolist(), [v, w],
            get_timeline_interface().get_current_time(), frame,
            behavior._first_inference_complete and not self.latch.is_held()
            and not behavior._is_backing_up and not behavior._waiting_for_inference_after_backup)
        state["backing_up"] = bool(behavior._is_backing_up)
        state["waiting_after_backup"] = bool(behavior._waiting_for_inference_after_backup)
        images = {}
        for name, rgb in [("third_person", behavior._camera_image_tp), ("front", behavior._camera_image_front)]:
            if rgb is None or not rgb.size:
                continue
            bgr = cv2.cvtColor(rgb[:, :, :3], cv2.COLOR_RGB2BGR)
            if name == "third_person":
                self.draw_line(bgr, self.path, matrix, (40, 164, 250), 5)
                self.draw_line(bgr, plan, matrix, (225, 216, 40), 6)
                if state["camera_view"] == "top_down":
                    goal = None
                    if self.distance_meter.origin is not None:
                        goal = [self.distance_meter.origin[i] + 3.0 * self.distance_meter.heading[i] for i in range(2)]
                    markers = [(self.path[0], "START", (255,255,255))]
                    if goal is not None:
                        markers.append(([float(goal[0]), float(goal[1]), 0.06], "3m REFERENCE", (90,230,120)))
                    for point, text, color in markers:
                        pixel = project_points([point], matrix, bgr.shape[1], bgr.shape[0])[0]
                        if pixel is not None:
                            cv2.circle(bgr, pixel, 9, color, 2, cv2.LINE_AA)
                            cv2.putText(bgr, text, (pixel[0]+13,pixel[1]-7), cv2.FONT_HERSHEY_SIMPLEX, .55, color, 2, cv2.LINE_AA)
                probe = state["distance_probe"]
                if probe is not None:
                    language = "Chinese" if any(ord(c) > 127 for c in behavior._instruction) else "English"
                    rows = [f"COMMAND: GO STRAIGHT 3m THEN STOP ({language} input)",
                            f"Forward {probe['forward_m']:.2f}m / 3.00m   Cross-track {probe['lateral_m']:+.2f}m   Path {probe['sampled_path_length_m']:.2f}m",
                            f"Actual speed {probe['actual_planar_speed_m_s']:.2f}m/s   Yaw {probe['actual_yaw_rate_rad_s']:+.2f}rad/s",
                            "MEASUREMENT ONLY: no automatic stop at 3m"]
                    cv2.rectangle(bgr, (0, bgr.shape[0]-119), (bgr.shape[1], bgr.shape[0]), (25,25,25), -1)
                    for n, row in enumerate(rows):
                        cv2.putText(bgr, row, (18, bgr.shape[0]-92+n*26), cv2.FONT_HERSHEY_SIMPLEX, .56, (255,255,255), 1, cv2.LINE_AA)
                label = "HOLD" if self.latch.is_held() else "NAVIGATING"
                if state["camera_view"] == "top_down":
                    label = "TOP VIEW / " + label
                cv2.putText(bgr, f"{label}  frame {frame}  wall {state['elapsed_wall_seconds']:.1f}s",
                            (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255,255,255), 2, cv2.LINE_AA)
                cv2.putText(bgr, "CYAN: PLAN   ORANGE: DRIVEN", (18, 58),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,255,255), 1, cv2.LINE_AA)
            ok, encoded = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ok:
                raise RuntimeError("Failed to encode live camera")
            images[f"/{name}.jpg"] = encoded.tobytes()
            if name == "third_person":
                (self.directory / "frames" / f"{self.sequence:06d}.jpg").write_bytes(encoded.tobytes())
        with self.lock:
            self.images.update(images)
            self.state = state
            self.trace.write(json.dumps(state) + "\n")
        self.sequence += 1

    def close(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        self.trace.close()
        self.events.close()
