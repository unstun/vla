"""Headless Habitat-Sim worker driven over stdin/stdout JSON lines.

Runs in the separate Python 3.9 `sim_env` so habitat-sim never shares a process
with the Torch/CUDA model runtime. Observations are written to disk as lossless
PNG (RGB) and uint16 millimetre PNG (depth, the representation the upstream
Habitat evaluator itself uses) and referenced by path in the JSON replies.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

import habitat_sim


SENTINEL = '@@SIMJSON@@'


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def emit(obj):
    """Habitat's renderer writes a banner to stdout, so tag protocol lines."""
    print(SENTINEL + json.dumps(obj), flush=True)


def build_sim(a):
    backend = habitat_sim.SimulatorConfiguration()
    backend.scene_id = a.scene
    backend.enable_physics = False
    backend.gpu_device_id = a.gpu
    backend.random_seed = a.seed
    if a.lighting == 'default':
        # habitat_test_scenes ship with no light setup, so the GLB renders flat
        # and roughly 3x darker than the released real-world fixtures. Enable
        # Habitat's default lighting to bring exposure closer to that range.
        backend.override_scene_light_defaults = True
        backend.scene_light_setup = habitat_sim.gfx.DEFAULT_LIGHTING_KEY

    specs = []
    for uuid, stype in (('rgb', habitat_sim.SensorType.COLOR),
                        ('depth', habitat_sim.SensorType.DEPTH)):
        s = habitat_sim.CameraSensorSpec()
        s.uuid = uuid
        s.sensor_type = stype
        s.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
        s.resolution = [a.height, a.width]
        s.position = [0.0, a.sensor_height, 0.0]
        s.hfov = a.hfov
        specs.append(s)

    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = specs
    agent_cfg.height = a.agent_height
    agent_cfg.radius = a.agent_radius
    A, Act = habitat_sim.agent.ActionSpec, habitat_sim.agent.ActuationSpec
    agent_cfg.action_space = {
        'move_forward': A('move_forward', Act(amount=a.forward)),
        'turn_left': A('turn_left', Act(amount=a.turn)),
        'turn_right': A('turn_right', Act(amount=a.turn)),
        'look_up': A('look_up', Act(amount=a.tilt)),
        'look_down': A('look_down', Act(amount=a.tilt)),
    }
    sim = habitat_sim.Simulator(habitat_sim.Configuration(backend, [agent_cfg]))
    if a.navmesh and os.path.exists(a.navmesh):
        sim.pathfinder.load_nav_mesh(a.navmesh)
    sim.pathfinder.seed(a.seed)
    return sim


def yaw_from_quat(q):
    """Habitat agent yaw about +Y, measured from -Z (the camera forward axis)."""
    fwd = quat_rotate(q, np.array([0.0, 0.0, -1.0]))
    return float(np.arctan2(-fwd[0], -fwd[2]))


def quat_rotate(q, v):
    w, x, y, z = float(q.w), float(q.x), float(q.y), float(q.z)
    u = np.array([x, y, z])
    return 2.0 * np.dot(u, v) * u + (w * w - np.dot(u, u)) * v + 2.0 * w * np.cross(u, v)


class Worker:
    def __init__(self, a):
        self.a = a
        self.sim = build_sim(a)
        self.obs_dir = a.out
        os.makedirs(self.obs_dir, exist_ok=True)
        self.uid = 0
        f = a.width / (2.0 * np.tan(np.deg2rad(a.hfov) / 2.0))
        self.intrinsic = [[f, 0.0, a.width / 2.0, 0.0],
                          [0.0, f, a.height / 2.0, 0.0],
                          [0.0, 0.0, 1.0, 0.0],
                          [0.0, 0.0, 0.0, 1.0]]

    def capture(self, obs, tag, collided=False):
        rgb = obs['rgb'][:, :, :3].astype(np.uint8)
        depth_m = np.asarray(obs['depth'], dtype=np.float32)
        depth_m = np.nan_to_num(depth_m, nan=0.0, posinf=0.0, neginf=0.0)
        depth_m = np.clip(depth_m, 0.0, self.a.max_depth)
        mm = np.clip(depth_m * 1000.0, 0, 65535).astype(np.uint16)

        rgb_path = os.path.join(self.obs_dir, '%s_%05d_rgb.png' % (tag, self.uid))
        depth_path = os.path.join(self.obs_dir, '%s_%05d_depth_mm.png' % (tag, self.uid))
        Image.fromarray(rgb).save(rgb_path)
        Image.fromarray(mm).save(depth_path)

        st = self.sim.get_agent(0).get_state()
        p = np.asarray(st.position, dtype=np.float64)
        reply = {
            'uid': self.uid,
            'rgb_path': rgb_path,
            'depth_path': depth_path,
            'position': p.tolist(),
            'rotation_wxyz': [float(st.rotation.w), float(st.rotation.x),
                              float(st.rotation.y), float(st.rotation.z)],
            'yaw_rad': yaw_from_quat(st.rotation),
            'collided': bool(collided),
            'depth_valid_fraction': float((depth_m > 1e-6).mean()),
            'depth_min_m': float(depth_m.min()),
            'depth_max_m': float(depth_m.max()),
            'depth_mean_m': float(depth_m.mean()),
        }
        self.uid += 1
        return reply

    def geodesic(self, a_pt, b_pt):
        path = habitat_sim.ShortestPath()
        path.requested_start = np.asarray(a_pt, dtype=np.float32)
        path.requested_end = np.asarray(b_pt, dtype=np.float32)
        ok = self.sim.pathfinder.find_path(path)
        return (float(path.geodesic_distance) if ok else None)

    def handle(self, req):
        cmd = req['cmd']
        if cmd == 'info':
            pf = self.sim.pathfinder
            bounds = [np.asarray(b).tolist() for b in pf.get_bounds()]
            return {'ok': True, 'navmesh_loaded': bool(pf.is_loaded),
                    'navigable_area': float(pf.navigable_area),
                    'bounds': bounds, 'intrinsic': self.intrinsic,
                    'lighting': self.a.lighting,
                    'habitat_sim': habitat_sim.__version__}
        if cmd == 'sample':
            pts = []
            for _ in range(int(req.get('n', 10))):
                p = self.sim.pathfinder.get_random_navigable_point()
                pts.append({'point': np.asarray(p).tolist(),
                            'island_radius': float(self.sim.pathfinder.island_radius(p))})
            return {'ok': True, 'points': pts}
        if cmd == 'reset':
            st = habitat_sim.AgentState()
            st.position = np.asarray(req['position'], dtype=np.float32)
            yaw = float(req.get('yaw_rad', 0.0))
            st.rotation = np.quaternion(np.cos(yaw / 2.0), 0.0, np.sin(yaw / 2.0), 0.0)
            self.sim.get_agent(0).set_state(st)
            obs = self.sim.get_sensor_observations()
            r = self.capture(obs, req.get('tag', 'reset'))
            r['ok'] = True
            return r
        if cmd == 'step':
            action = req['action']
            if action == 'noop':
                obs = self.sim.get_sensor_observations()
                collided = False
            else:
                obs = self.sim.step(action)
                collided = bool(getattr(self.sim, 'previous_step_collided', False))
            r = self.capture(obs, req.get('tag', 'step'), collided)
            r['ok'] = True
            r['action'] = action
            return r
        if cmd == 'topdown':
            mpp = float(req.get('meters_per_pixel', 0.05))
            height = float(req['height'])
            view = np.asarray(self.sim.pathfinder.get_topdown_view(mpp, height))
            path = os.path.join(self.obs_dir, 'topdown_h%.2f.png' % height)
            Image.fromarray((view.astype(np.uint8) * 255)).save(path)
            b = self.sim.pathfinder.get_bounds()
            return {'ok': True, 'path': path, 'shape': list(view.shape),
                    'meters_per_pixel': mpp, 'height': height,
                    'origin_xz': [float(b[0][0]), float(b[0][2])]}
        if cmd == 'geodesic':
            return {'ok': True, 'geodesic': self.geodesic(req['from'], req['to'])}
        if cmd == 'close':
            self.sim.close()
            return {'ok': True, 'closed': True}
        return {'ok': False, 'error': 'unknown cmd %s' % cmd}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--scene', required=True)
    p.add_argument('--navmesh', default='')
    p.add_argument('--out', required=True)
    p.add_argument('--width', type=int, default=640)
    p.add_argument('--height', type=int, default=480)
    p.add_argument('--hfov', type=float, default=79.0)
    p.add_argument('--sensor-height', type=float, default=1.25)
    p.add_argument('--agent-height', type=float, default=1.5)
    p.add_argument('--agent-radius', type=float, default=0.1)
    p.add_argument('--forward', type=float, default=0.25)
    p.add_argument('--turn', type=float, default=15.0)
    p.add_argument('--tilt', type=float, default=15.0)
    p.add_argument('--max-depth', type=float, default=10.0)
    p.add_argument('--gpu', type=int, default=0)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--lighting', choices=['scene', 'default'], default='scene')
    a = p.parse_args()

    w = Worker(a)
    log('WORKER_READY')
    emit({'ok': True, 'event': 'ready'})
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        try:
            reply = w.handle(req)
        except Exception as exc:  # keep the loop alive so failures are recorded
            import traceback
            reply = {'ok': False, 'error': str(exc), 'traceback': traceback.format_exc()}
        emit(reply)
        if req.get('cmd') == 'close':
            break


if __name__ == '__main__':
    main()
