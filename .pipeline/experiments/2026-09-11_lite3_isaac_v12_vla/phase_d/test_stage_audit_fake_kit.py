#!/usr/bin/env python3
"""Smoke test of phase_d/stage_audit.py end to end, with fake Isaac Lab / omni.physx / carb / torch / PIL modules.

    PYTHONPATH=<dir holding only numpy> <python with usd-core> phase_d/test_stage_audit_fake_kit.py

It cannot show Isaac behaviour; it exists so that the single real start cannot die on a Python error in a branch no
local test executes, and so that the record run() writes is the record evaluate() reads. The fakes copy the failure
modes the pre-GPU review raised:
- the GPU pipeline does not refresh get_rigidbody_transformation (U1): only the rigid-body view sees the probe fall;
- a list rigid-body view is refused when it contains the nested dynamic door body, so per-body views are needed;
- the first two frames are black (render warm-up);
- a carpet collider lies over the floor under pose B;
- a variant where Camera.set_world_poses silently does nothing must fail the pose-B render check.
The synthetic scene is phase_d/test_stage_audit.py build_scene (InteriorAgent authoring layout).
"""
import copy
import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import types

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
RESULTS = []


def check(name, cond, detail=''):
    RESULTS.append((name, bool(cond)))
    print('{} {}{}'.format('PASS' if cond else 'FAIL', name, ' - ' + str(detail)[:600] if detail and not cond else ''))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeTensor:
    def __init__(self, array):
        import numpy as np
        self.a = np.asarray(array)

    def __getitem__(self, item):
        return FakeTensor(self.a[item])

    def cpu(self):
        return self

    def detach(self):
        return self

    def clone(self):
        return FakeTensor(self.a.copy())

    def numpy(self):
        return self.a

    def to(self, dtype):
        return FakeTensor(self.a.astype(dtype))

    def tolist(self):
        return self.a.tolist()


def install_fakes(variant):
    import numpy as np
    from pxr import Gf, Usd, UsdGeom, UsdPhysics

    world = {'stage': None, 'sim': None, 'cameras': [], 'closed': False}

    torch = types.ModuleType('torch')
    torch.uint8, torch.float32 = np.uint8, np.float32
    torch.tensor = lambda data, dtype=None, device=None: FakeTensor(np.array(data, dtype=dtype or np.float64))
    pil = types.ModuleType('PIL')
    pil_image = types.ModuleType('PIL.Image')

    class _Img:
        def __init__(self, arr):
            self.arr = arr

        def save(self, path):
            pathlib.Path(path).write_bytes(b'PNG' + np.asarray(self.arr).tobytes()[:64])
    pil_image.fromarray = _Img
    pil.Image = pil_image

    carb = types.ModuleType('carb')
    carb.Float3 = lambda *v: tuple(float(x) for x in v)
    carb.Float4 = lambda *v: tuple(float(x) for x in v)

    isaaclab = types.ModuleType('isaaclab')
    app_mod = types.ModuleType('isaaclab.app')

    class AppLauncher:
        def __init__(self, headless, enable_cameras, device):
            stage = Usd.Stage.CreateInMemory()
            UsdGeom.SetStageMetersPerUnit(stage, 1.0)
            UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
            world['stage'] = stage
            self.app = types.SimpleNamespace(close=lambda: world.__setitem__('closed', True))
    app_mod.AppLauncher = AppLauncher

    sim_mod = types.ModuleType('isaaclab.sim')

    class Cfg:
        def __init__(self, **kw):
            self.__dict__.update(kw)
    for name in ('SimulationCfg', 'PinholeCameraCfg', 'RigidBodyPropertiesCfg', 'MassPropertiesCfg',
                 'CollisionPropertiesCfg'):
        setattr(sim_mod, name, type(name, (Cfg,), {}))

    def physx_cfg(**kw):
        allowed = {'gpu_collision_stack_size', 'gpu_max_rigid_contact_count', 'gpu_max_rigid_patch_count',
                   'gpu_found_lost_pairs_capacity', 'gpu_found_lost_aggregate_pairs_capacity',
                   'gpu_total_aggregate_pairs_capacity', 'gpu_max_soft_body_contacts', 'gpu_max_particle_contacts'}
        assert set(kw) <= allowed, set(kw) - allowed
        return Cfg(**kw)
    sim_mod.PhysxCfg = physx_cfg

    def create_prim(prim_path, prim_type='Xform', translation=None, orientation=None, usd_path=None, **kw):
        stage = world['stage']
        assert not stage.GetPrimAtPath(prim_path).IsValid(), 'prim exists: ' + prim_path
        prim = stage.DefinePrim(prim_path, prim_type)
        if usd_path:
            prim.GetReferences().AddReference(usd_path)
        xf = UsdGeom.Xformable(prim)
        if translation is not None:
            xf.AddTranslateOp().Set(Gf.Vec3d(*translation))
        if orientation is not None:
            w, x, y, z = orientation
            xf.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(w, x, y, z))
        return prim
    sim_mod.create_prim = create_prim
    sim_mod.get_current_stage = lambda: world['stage']

    class CuboidCfg(Cfg):
        def func(self, prim_path, cfg, translation=None):
            prim = create_prim(prim_path, 'Xform', translation=translation)
            world['stage'].DefinePrim(prim_path + '/geometry/mesh', 'Cube')
            if cfg.rigid_props is not None:
                UsdPhysics.RigidBodyAPI.Apply(prim)
            return prim
    sim_mod.CuboidCfg = CuboidCfg

    class RigidBodyView:
        def __init__(self, sim, paths):
            self.sim, self._backend = sim, object()
            self._paths = paths

        @property
        def count(self):
            return len(self._paths)

        @property
        def prim_paths(self):
            return list(self._paths)

        def get_transforms(self):
            rows = []
            n = self.sim.steps
            for p in self._paths:
                if p == '/World/ReadoutProbe':
                    rows.append([200.0, 200.0, 10.0 - 9.81 * 0.005 ** 2 * n * (n + 1) / 2, 0, 0, 0, 1])
                else:
                    m = UsdGeom.XformCache().GetLocalToWorldTransform(world['stage'].GetPrimAtPath(p))
                    t = m.ExtractTranslation()
                    rows.append([t[0], t[1], t[2], 0, 0, 0, 1])
            return FakeTensor(np.array(rows, dtype=np.float32))

    class SimView:
        def __init__(self, sim):
            self.sim = sim

        def create_rigid_body_view(self, pattern):
            paths = [pattern] if isinstance(pattern, str) else list(pattern)
            if any('group_0000' in p for p in paths):
                raise RuntimeError('nested rigid body refused (fake)')
            for p in paths:
                if not world['stage'].GetPrimAtPath(p).HasAPI(UsdPhysics.RigidBodyAPI):
                    raise RuntimeError('not a rigid body: ' + p)
            return RigidBodyView(self.sim, paths)

    class SimulationContext:
        def __init__(self, cfg):
            assert cfg.enable_scene_query_support is True and cfg.dt == 0.005 and cfg.render_interval == 4
            UsdPhysics.Scene.Define(world['stage'], '/physicsScene')
            self.steps, self.renders, self.device, self._reset = 0, 0, 'cpu', False
            world['sim'] = self

        def reset(self):
            self._reset, self.steps = True, 0
            for cam in world['cameras']:
                cam._initialize()

        @property
        def physics_sim_view(self):
            assert self._reset, 'physics_sim_view before reset'
            return SimView(self)

        def step(self, render=True):
            assert self._reset
            self.steps += 1

        def render(self):
            self.renders += 1

        def clear_all_callbacks(self):
            world['callbacks_cleared'] = True

        def clear_instance(self):
            world['instance_cleared'] = True
    sim_mod.SimulationContext = SimulationContext

    sensors = types.ModuleType('isaaclab.sensors')

    class CameraCfg(Cfg):
        class OffsetCfg(Cfg):
            pass

    class _View:
        def __init__(self, cam):
            self.cam = cam

        def get_world_poses(self):
            return FakeTensor([list(self.cam.world_pos)]), FakeTensor([[1.0, 0, 0, 0]])

    class Camera:
        def __init__(self, cfg):
            self.cfg = cfg
            parent = cfg.prim_path.rsplit('/', 1)[0]
            assert world['stage'].GetPrimAtPath(parent).IsValid(), 'camera parent missing'
            world['stage'].DefinePrim(cfg.prim_path, 'Camera')
            world['cameras'].append(self)
            self.frame = 0
            self._view = None

        def _initialize(self):
            parent = world['stage'].GetPrimAtPath(self.cfg.prim_path.rsplit('/', 1)[0])
            m = UsdGeom.XformCache().GetLocalToWorldTransform(parent)
            p = m.Transform(Gf.Vec3d(*self.cfg.offset.pos))
            self.world_pos = (p[0], p[1], p[2])
            self._view = _View(self)

        def set_world_poses(self, positions=None, orientations=None, convention='ros'):
            assert convention == 'ros' and self._view is not None
            if variant != 'camera_move_ignored':
                self.world_pos = tuple(positions.a[0].tolist())

        def update(self, dt):
            self.frame += 1

        @property
        def data(self):
            rng = np.random.default_rng(self.frame)
            h, w = self.cfg.height, self.cfg.width
            out = {'rgb': FakeTensor(np.zeros((1, h, w, 3), np.uint8) if self.frame <= 2 else
                                     rng.integers(20, 230, size=(1, h, w, 3), dtype=np.uint8))}
            if 'distance_to_image_plane' in self.cfg.data_types:
                out['distance_to_image_plane'] = FakeTensor(np.full((1, h, w, 1), 2.5, np.float32))
            return types.SimpleNamespace(output=out)
    sensors.Camera, sensors.CameraCfg = Camera, CameraCfg

    omni = types.ModuleType('omni')
    physx = types.ModuleType('omni.physx')
    lib = load(HERE / 'stage_audit_lib.py', 'lib_for_fake_physx')
    thr = json.loads((HERE / 'stage_audit_thresholds_d1b.json').read_text())

    def rows():
        return [r for r in lib.object_inventory_at(world['stage'], '/World/Scene', thr) if r['aabb_min']]

    class Hit:
        def __init__(self, collision, distance=0.0):
            self.collision, self.rigid_body, self.distance = collision, collision, distance

    def collider_path(row):
        return row['colliders'][0]['path'] if row['colliders'] else None

    class SQ:
        def overlap_box(self, half, center, rot, report, any_hit):
            hits = []
            for row in rows():
                col = collider_path(row)
                if col and all(row['aabb_min'][i] <= center[i] + half[i] and row['aabb_max'][i] >= center[i] - half[i]
                               for i in range(3)):
                    hits.append(Hit(col))
            for hit in hits:
                if not report(hit):
                    break
            return len(hits)

        def _down(self, origin, direction, length):
            if direction != (0.0, 0.0, -1.0):
                return []
            out = []
            for row in rows():
                col = collider_path(row)
                if col and row['aabb_min'][0] <= origin[0] <= row['aabb_max'][0] and \
                        row['aabb_min'][1] <= origin[1] <= row['aabb_max'][1] and row['aabb_max'][2] < origin[2]:
                    out.append(Hit(col, origin[2] - row['aabb_max'][2]))
            return sorted([h for h in out if h.distance <= length], key=lambda h: h.distance)

        def raycast_all(self, origin, direction, length, report, both_sides=False):
            for hit in self._down(origin, direction, length):
                if not report(hit):
                    break
            return True

        def raycast_closest(self, origin, direction, length, both_sides=False):
            hits = self._down(origin, direction, length)
            if not hits:
                return {'hit': False}
            return {'hit': True, 'collision': hits[0].collision, 'distance': hits[0].distance}

    class PX:
        def get_rigidbody_transformation(self, path):       # stale under the GPU pipeline (review U1)
            m = UsdGeom.XformCache().GetLocalToWorldTransform(world['stage'].GetPrimAtPath(path))
            t = m.ExtractTranslation()
            return {'ret_val': True, 'position': (t[0], t[1], t[2]), 'rotation': (0.0, 0.0, 0.0, 1.0)}
    physx.get_physx_scene_query_interface = SQ
    physx.get_physx_interface = PX
    omni.physx = physx

    for name, module in {'torch': torch, 'PIL': pil, 'PIL.Image': pil_image, 'carb': carb, 'isaaclab': isaaclab,
                         'isaaclab.app': app_mod, 'isaaclab.sim': sim_mod, 'isaaclab.sensors': sensors,
                         'omni': omni, 'omni.physx': physx}.items():
        sys.modules[name] = module
    return world


def run_variant(tmp, variant):
    test_mod = load(HERE / 'test_stage_audit.py', 'tsa_' + variant)
    scene = test_mod.build_scene(tmp / ('scene_' + variant))
    thr = json.loads((HERE / 'stage_audit_thresholds_d1b.json').read_text())
    thr = copy.deepcopy(thr)
    thr['poses']['A'] = {'source': 'fake', 'xy': [2.5, -2.0], 'yaw_deg': 90.0}
    thr['poses']['B'] = {'source': 'fake, on the carpet', 'xy': [0.2, 0.2], 'yaw_deg': -18.413}
    thr_path = tmp / ('thr_' + variant + '.json')
    thr_path.write_text(json.dumps(thr, indent=2))
    eps = tmp / ('eps_' + variant + '.json')
    eps.write_text(json.dumps({'episodes': [
        {'episode_id': 1, 'start_position': [2.5, -2.0, 0], 'goals': {'position': [0.2, 0.2, 0]}}]}))
    out = tmp / ('out_' + variant)
    world = install_fakes(variant)
    for mod in ('stage_audit', 'stage_audit_lib', 'phase_b_camera_probe'):
        sys.modules.pop(mod, None)
    sa = load(HERE / 'stage_audit.py', 'stage_audit_' + variant)
    rc = sa.main(['--scene-usd', str(scene / 'kujiale_test.usda'), '--episodes', str(eps), '--thresholds', str(thr_path),
                  '--fusion-config', str(HERE / 'fusion_isaac_c8.json'),
                  '--chase-episode', str(EXP / 'phase_c' / 'episodes' / 'c_red_box_ahead_v1.json'),
                  '--tools-dir', str(EXP / 'scripts'), '--output-dir', str(out), '--device', 'cpu'])
    result = json.loads((out / 'stage_audit_result.json').read_text())
    return rc, result, out, world


def main():
    try:
        import numpy  # noqa: F401
        import pxr  # noqa: F401
    except ImportError as exc:
        print('SKIP: needs usd-core and numpy in one interpreter ({})'.format(exc))
        return 2
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir).resolve()
        rc, result, out, world = run_variant(tmp, 'good')
        marker = out / 'STAGE_AUDIT_COMPLETE'
        check('run: completes, marker matches the atomic result file',
              rc == 0 and marker.exists() and not (out / 'STAGE_AUDIT_ERROR').exists()
              and marker.read_text().strip() == hashlib.sha256((out / 'stage_audit_result.json').read_bytes()).hexdigest(),
              result.get('error'))
        check('run: no section errors', not result['static_errors'] and not result['section_errors'],
              {**result['static_errors'], **result['section_errors']})
        marks = [m['mark'] for m in result['marks']]
        journal = [json.loads(line)['mark'] for line in (out / 'marks.jsonl').read_text().splitlines()]
        order = ['app_started', 'static_audit_done', 'sim_context', 'scene_referenced', 'cameras_spawned',
                 'sim_reset_done', 'collision_probes_done', 'physics_checked', 'render_A_done', 'render_B_done']
        check('run: marks in order; "complete" only in marks.jsonl (written after the hashed result)',
              marks == order and journal == order + ['complete'], (marks, journal))
        ph = result['physics']
        check('physics: the stale second readout is rejected by the probe, the view readout is used',
              ph['readout'] == 'rigid_body_view' and ph['probes_by_readout']['rigid_body_view']['ok']
              and not ph['probes_by_readout']['get_rigidbody_transformation']['ok'], ph.get('probes_by_readout'))
        door = [b for b in ph['bodies'] if b['path'].endswith('group_0000')]
        check('physics: the refused list view falls back to per-body views; the door body is listed not found',
              ph['view_error'] and ph['views'] > 1 and door and door[0]['found'] is False, ph.get('view_error'))
        check('physics: 200 steps = 1.0 s', ph['physics_steps'] == 200 and ph['simulated_s'] == 1.0)
        ra = result['render']['A']
        check('render: first two black frames skipped, first valid at iteration 2, clock from reset end',
              ra['first_valid_iteration'] == 2 and ra['consecutive_valid_max'] >= 3 and ra['iterations'] == 120
              and ra['clock_origin'] == 'end of sim.reset()', {k: ra.get(k) for k in ('first_valid_iteration', 'iterations')})
        frames = sorted(p.name for p in (out / 'frames').iterdir())
        check('render: frames saved for both poses (iter000, firstvalid, last)',
              len([f for f in frames if f.endswith('.png')]) == 2 * 3 * 4 and len([f for f in frames if f.endswith('.npy')]) == 12,
              frames[:6])
        rays = result['collision']['floor_rays']
        check('collision: floor under A; under B the carpet is closest and the floor still found',
              rays['A']['floor_hit'] and rays['B']['closest']['class'] == 'rug' and rays['B']['floor_hit']['class'] == 'floor',
              rays)
        check('readback: cameras at A and moved to B', result['render']['poses_check']['A']['ok']
              and result['render']['poses_check']['B']['ok'], result['render']['poses_check'])
        gate = result['gate_in_run']
        check('gate in run: only the memory check is open (it needs the host samples)',
              gate['failed'] == ['M1_isaac_gpu_peak'], [c for c in gate['checks'] if c['verdict'] != 'PASS'])
        cleanup = json.loads((out / 'cleanup.json').read_text())
        check('shutdown: cameras, callbacks, instance, then app close',
              cleanup['steps'] == ['cameras deleted', 'clear_all_callbacks', 'clear_instance'] and world['closed'], cleanup)

        rc, result, out, world = run_variant(tmp, 'camera_move_ignored')
        gate = result['gate_in_run']
        check('variant: a silently ignored camera move fails the pose-B render check only',
              gate['failed'] == ['R_frames_valid_pose_B', 'M1_isaac_gpu_peak'] and
              not result['render']['poses_check']['B']['ok'], gate['failed'])
    failed = [n for n, ok in RESULTS if not ok]
    print('{}/{} checks passed'.format(len(RESULTS) - len(failed), len(RESULTS)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
