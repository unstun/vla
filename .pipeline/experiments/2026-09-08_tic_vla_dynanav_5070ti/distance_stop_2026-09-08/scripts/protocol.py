"""The bounded demo vocabulary and coordinate contract; no robot dependencies."""
import math
import re
import threading

INSTRUCTION = "Go straight ahead and stop at the front of the vending machine."
GOALS = {"走到自动售货机前", "走到自动售货机前面", "去自动售货机", "到自动售货机前",
         "走到售货机前", "去售货机", "直走并在自动售货机前停下", "直走在自动售货机前停下",
         "go to the vending machine", INSTRUCTION.lower().rstrip(".")}
from distance_probe import INSTRUCTION as DISTANCE_INSTRUCTION
GOALS.add(re.sub(r"[。！？!?,，.;；]", "", DISTANCE_INSTRUCTION))
STOPS = {"停", "停下", "停止", "停车", "暂停", "停下来", "stop", "pause"}
RESUMES = {"继续", "继续走", "继续前进", "resume", "continue"}


def parse_command(text):
    if not isinstance(text, str) or not 1 <= len(text) <= 240:
        raise ValueError("请输入一句简短指令。")
    normalized = re.sub(r"[。！？!?,，.;；]", "", text).strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    if normalized in GOALS:
        action = "goal"
    elif normalized in STOPS:
        action = "stop"
    elif normalized in RESUMES:
        action = "resume"
    else:
        raise ValueError("本演示支持：走到自动售货机前、停下、继续。请重新说一次或输入文字。")
    return {"action": action, "instruction": text.strip() if action == "goal" else None,
            "text": text.strip()}


def read_instruction_request(path):
    """Validate a bounded UTF-8 request without translating or substituting text."""
    import json
    data = path.read_bytes()
    if len(data) > 4096:
        raise ValueError("Instruction request too large")
    payload = json.loads(data.decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("instruction_mode") != "verbatim":
        raise ValueError("A verbatim instruction request is required")
    command = parse_command(payload.get("instruction"))
    if command["action"] != "goal":
        raise ValueError("Offline input must be a navigation goal")
    if command["instruction"] != payload["instruction"]:
        raise ValueError("Request text must already be trimmed")
    seed = payload.get("inference_seed")
    if seed is not None and (type(seed) is not int or not 0 <= seed < 2**32):
        raise ValueError("Inference seed must be an integer in [0, 2**32)")
    return payload


class CommandLatch:
    """HTTP owns submission; simulator owns acknowledgement and releasing hold."""
    def __init__(self):
        self.lock = threading.Lock()
        self.epoch = 0
        self.held = True
        self.pending = None
        self.last_command = None
        self.ack = None
        self.has_goal = False
        self.seen = {}

    def submit(self, payload):
        parsed = parse_command(payload.get("text"))
        identity = payload.get("id")
        if not isinstance(identity, str) or not 1 <= len(identity) <= 80:
            raise ValueError("Missing command ID")
        with self.lock:
            if identity in self.seen:
                return dict(self.seen[identity], duplicate=True)
            if parsed["action"] == "resume" and not self.has_goal:
                raise ValueError("请先下达前往自动售货机的指令。")
            self.epoch += 1
            self.held = True
            if parsed["action"] == "goal":
                self.has_goal = True
            self.pending = dict(parsed, id=identity, epoch=self.epoch)
            self.last_command = self.pending.copy()
            self.seen[identity] = self.pending.copy()
            return self.pending.copy()

    def take(self):
        with self.lock:
            pending, self.pending = self.pending, None
            return pending

    def acknowledge(self, command):
        with self.lock:
            if command["epoch"] == self.epoch:
                self.held = command["action"] == "stop"
                self.ack = command.copy()

    def is_held(self):
        with self.lock:
            return self.held

    def snapshot(self):
        with self.lock:
            return {"held": self.held, "command_epoch": self.epoch,
                    "last_command": self.last_command, "ack": self.ack}


def body_to_world(points, position, quaternion):
    """Body FLU x/y in metres, quaternion wxyz; preserve the captured yaw."""
    w, x, y, z = quaternion
    yaw = math.atan2(2 * (w*z + x*y), 1 - 2 * (y*y + z*z))
    c, s = math.cos(yaw), math.sin(yaw)
    return [[position[0] + c*p[0] - s*p[1], position[1] + s*p[0] + c*p[1], 0.06]
            for p in points]


def project_points(points, world_to_clip, width, height):
    """USD/Gf row-vector homogeneous matrix to top-left-origin image pixels."""
    projected = []
    for point in points:
        v = [*point, 1.0]
        clip = [sum(v[i] * world_to_clip[i][j] for i in range(4)) for j in range(4)]
        if clip[3] <= 1e-5:
            projected.append(None)
            continue
        px = (clip[0] / clip[3] + 1) * width / 2
        py = (1 - clip[1] / clip[3]) * height / 2
        projected.append([int(max(-100000, min(100000, px))), int(max(-100000, min(100000, py)))])
    return projected
