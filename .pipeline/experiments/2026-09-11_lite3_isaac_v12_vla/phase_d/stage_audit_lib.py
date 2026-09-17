"""Phase D.1b stage audit: the parts that need neither Kit nor a GPU.

- USD inventory of a scene (pxr only): dependencies, units, physics authoring per object, object groups.
- Scene-query decision logic (own-hit overlap with subdivision, floor ray), rigid-body motion, pose readback.
- Pose and quaternion helpers for the camera rig.
- Image metrics (numpy only).
- The gate: `evaluate(result, thresholds, isaac_peak_mib)` turns a run record into per-check verdicts.

pxr and numpy are imported inside the functions that need them, so the USD tests run with usd-core alone and the image
and gate tests with numpy alone. `phase_d/stage_audit.py` runs all of it inside the Isaac container.
"""
import math
import re

GPRIM_TYPES = ('Mesh', 'Cube', 'Sphere', 'Capsule', 'Cylinder', 'Cone', 'Plane', 'Points')


# ----------------------------------------------------------------------------------------------------------------
# USD inventory (pxr)
# ----------------------------------------------------------------------------------------------------------------

REPORTED_ONLY_ASSET_ATTRIBUTES = ('info:unreal:sourceAsset',)


def norm_path(path):
    """A resolver path without a file: URL scheme, so Kit's and usd-core's answers compare the same."""
    p = str(path)
    if p.startswith('file://'):
        return p[len('file://'):]
    if p.startswith('file:'):
        return p[len('file:'):]
    return p


def asset_attribute_values(layer_paths):
    """(attribute name, authored asset path) for every asset-valued attribute default in the given layers."""
    from pxr import Sdf

    found = []
    for path in layer_paths:
        layer = Sdf.Layer.FindOrOpen(path)
        if layer is None:
            continue

        def visit(spec_path, layer=layer):
            spec = layer.GetObjectAtPath(spec_path)
            if not isinstance(spec, Sdf.AttributeSpec):
                return
            if spec.typeName not in (Sdf.ValueTypeNames.Asset, Sdf.ValueTypeNames.AssetArray):
                return
            value = spec.default
            values = [value] if isinstance(value, Sdf.AssetPath) else (list(value) if value is not None else [])
            for asset in values:
                if asset.path:
                    found.append((spec.name, asset.path))
        layer.Traverse(Sdf.Path.absoluteRootPath, visit)
    return found


def dependency_report(root_layer_path, scene_root, allowed_mdl_roots=('/isaac-sim/',)):
    """Layers, assets and unresolved paths of a scene, split into what the gate counts and what it only reports.

    Reported, not counted (phase_d/stage_audit_thresholds_d1b.json stage.unresolved_reported_not_gated):
    - bare *.mdl module names such as `OmniPBR.mdl`, which Kit resolves on its MDL search path;
    - values of `info:unreal:sourceAsset`: Unreal content paths (`/Engine/...`, `/Game/...`) that the exporter left
      on each `UnrealShader` prim for the unreal render context. Kit renders the `info:mdl:sourceAsset` shader.
    Everything else that does not resolve (composition arcs, textures, the scene's own MDL files) is local
    unresolved and counted. non-local: a resolved layer or asset outside the scene folder, except MDL under Kit.
    """
    from pxr import UsdUtils

    layers, assets, unresolved = UsdUtils.ComputeAllDependencies(root_layer_path)
    scene_root = norm_path(scene_root).rstrip('/') + '/'
    raw_layers = [layer.realPath or layer.identifier for layer in layers]
    raw_assets = [str(a) for a in assets]
    layer_paths = sorted(norm_path(p) for p in raw_layers)
    asset_paths = sorted(norm_path(p) for p in raw_assets)
    unresolved = sorted(norm_path(u) for u in unresolved)
    attr_values = asset_attribute_values(layer_paths)
    metadata_values = {p for name, p in attr_values if name in REPORTED_ONLY_ASSET_ATTRIBUTES}
    other_values = {p for name, p in attr_values if name not in REPORTED_ONLY_ASSET_ATTRIBUTES}
    unreal_metadata = [u for u in unresolved if u in metadata_values and u not in other_values]
    bare_mdl = [u for u in unresolved if '/' not in u and '\\' not in u and u.lower().endswith('.mdl')]
    local_unresolved = [u for u in unresolved if u not in bare_mdl and u not in unreal_metadata]

    # MDL modules authored as bare names (OmniPBR.mdl) resolve wherever Kit keeps its MDL library; they are Kit's,
    # not the scene's, so they are reported by name whatever directory the resolver returns.
    bare_mdl_names = {p for name, p in attr_values
                      if name == 'info:mdl:sourceAsset' and '/' not in p and p.lower().endswith('.mdl')}

    def non_local(path):
        if path.startswith(scene_root):
            return False
        if path.lower().endswith('.mdl') and (any(path.startswith(root) for root in allowed_mdl_roots)
                                              or path.replace('\\', '/').rsplit('/', 1)[-1] in bare_mdl_names):
            return False
        return True

    non_local_paths = [p for p in layer_paths if not p.startswith(scene_root)] + \
        [p for p in asset_paths if non_local(p)]
    return {
        'layers': len(layer_paths), 'assets': len(asset_paths), 'unresolved_count': len(unresolved),
        'bare_mdl_unresolved': bare_mdl, 'unreal_metadata_unresolved_count': len(unreal_metadata),
        'unreal_metadata_examples': unreal_metadata[:5], 'local_unresolved': local_unresolved,
        'non_local': non_local_paths, 'layer_paths': layer_paths, 'asset_ext_counts': _ext_counts(asset_paths),
        'asset_attribute_counts': _name_counts(name for name, _ in attr_values),
        'raw_path_examples': {'layers': sorted(raw_layers)[:3], 'assets': sorted(raw_assets)[:3]},
    }


def _name_counts(names):
    counts = {}
    for n in names:
        counts[n] = counts.get(n, 0) + 1
    return dict(sorted(counts.items()))


def _ext_counts(paths):
    counts = {}
    for p in paths:
        ext = p.rsplit('.', 1)[-1].lower() if '.' in p.rsplit('/', 1)[-1] else ''
        counts[ext] = counts.get(ext, 0) + 1
    return dict(sorted(counts.items()))


def layer_units(layer_paths):
    """metersPerUnit and upAxis as authored on each USD layer (None when not authored or unreadable)."""
    from pxr import Sdf

    rows = []
    for path in layer_paths:
        if not re.search(r'\.usd[acz]?$', path):
            continue
        layer = Sdf.Layer.FindOrOpen(path)
        if layer is None:
            rows.append({'layer': path, 'meters_per_unit': None, 'up_axis': None, 'error': 'cannot open layer'})
            continue
        root = layer.pseudoRoot
        mpu = root.GetInfo('metersPerUnit') if root.HasInfo('metersPerUnit') else None
        up = root.GetInfo('upAxis') if root.HasInfo('upAxis') else None
        rows.append({'layer': path, 'meters_per_unit': mpu, 'up_axis': up})
    return rows


def _predicate():
    """Active, loaded, defined, non-abstract prims, through instance proxies (the default traversal, plus proxies)."""
    from pxr import Usd

    return Usd.TraverseInstanceProxies(Usd.PrimDefaultPredicate)


def _class_of(prim, predicate=None):
    """Semantic class of an object: the shallowest authored semanticData in its subtree, else its name.

    InteriorAgent references each object file without a target prim, so the file's defaultPrim `/Root` composes under
    the object and the labelled prim sits at `<object>/Meshes/<name>` (checked on kujiale_0021 samples).
    """
    queue = [prim]
    predicate = predicate or _predicate()
    while queue:
        current = queue.pop(0)
        attr = current.GetAttribute('semantic:Semantics:params:semanticData')
        if attr and attr.HasAuthoredValue():
            return str(attr.Get()), 'semantics'
        queue.extend(current.GetFilteredChildren(predicate))
    return re.sub(r'_\d+$', '', prim.GetName()), 'name'


def _approximation(prim):
    from pxr import UsdPhysics

    if prim.HasAPI(UsdPhysics.MeshCollisionAPI):
        return str(UsdPhysics.MeshCollisionAPI(prim).GetApproximationAttr().Get())
    return None


def object_inventory(stage, thresholds):
    """One row per object: every direct child of a room Scope under <defaultPrim>/Meshes (the InteriorAgent layout)."""
    default = stage.GetDefaultPrim()
    if not default:
        raise ValueError('stage has no default prim')
    return object_inventory_at(stage, str(default.GetPath()), thresholds)


def _meshes_root(stage, root_path):
    from pxr import Sdf

    meshes_root = stage.GetPrimAtPath(Sdf.Path(root_path).AppendChild('Meshes'))
    if not meshes_root or not meshes_root.IsValid():
        raise ValueError('no {}/Meshes scope in this stage'.format(root_path))
    return meshes_root


def inventory_exclusions(stage, root_path):
    """Room and object children that the default predicate skips (inactive, over-only, abstract, unloaded)."""
    from pxr import Usd

    excluded = []
    everything = Usd.TraverseInstanceProxies(Usd.PrimAllPrimsPredicate)
    kept = _predicate()
    for room in _meshes_root(stage, root_path).GetFilteredChildren(everything):
        candidates = [room] + list(room.GetFilteredChildren(everything))
        for prim in candidates:
            if not kept(prim):
                excluded.append({'path': str(prim.GetPath()), 'active': prim.IsActive(), 'defined': prim.IsDefined(),
                                 'abstract': prim.IsAbstract(), 'loaded': prim.IsLoaded()})
    return excluded


def object_inventory_at(stage, root_path, thresholds):
    """The same inventory for a scene whose root prim sits at `root_path` (e.g. referenced at /World/Scene)."""
    from pxr import Usd, UsdGeom, UsdPhysics

    cls_cfg = thresholds['classification']
    meshes_root = _meshes_root(stage, root_path)
    predicate = _predicate()
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render],
                              useExtentsHint=False)
    rows = []
    for room in meshes_root.GetFilteredChildren(predicate):
        for obj in room.GetFilteredChildren(predicate):
            cls, cls_source = _class_of(obj, predicate)
            rng = cache.ComputeWorldBound(obj).ComputeAlignedRange()
            empty = rng.IsEmpty()
            lo = [float(v) for v in rng.GetMin()] if not empty else None
            hi = [float(v) for v in rng.GetMax()] if not empty else None
            colliders, bodies, joints, meshes, triangles, merge = [], [], 0, 0, 0, 0
            for prim in Usd.PrimRange(obj, predicate):
                type_name = prim.GetTypeName()
                if prim.IsA(UsdGeom.Mesh):
                    meshes += 1
                    counts = UsdGeom.Mesh(prim).GetFaceVertexCountsAttr().Get() or []
                    triangles += sum(max(0, int(n) - 2) for n in counts)
                if prim.IsA(UsdPhysics.Joint):
                    joints += 1
                if 'PhysxMeshMergeCollisionAPI' in [str(s) for s in prim.GetAppliedSchemas()]:
                    merge += 1
                if prim.HasAPI(UsdPhysics.CollisionAPI):
                    enabled = UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get()
                    colliders.append({'path': str(prim.GetPath()), 'type': type_name,
                                      'gprim': type_name in GPRIM_TYPES, 'approximation': _approximation(prim),
                                      'enabled': bool(enabled) if enabled is not None else True})
                if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                    api = UsdPhysics.RigidBodyAPI(prim)
                    kin, on = api.GetKinematicEnabledAttr().Get(), api.GetRigidBodyEnabledAttr().Get()
                    bodies.append({'path': str(prim.GetPath()), 'kinematic': bool(kin), 'enabled': bool(on)})
            body_paths = [b['path'] for b in bodies]
            nested = [b for b in body_paths if any(b != a and b.startswith(a + '/') for a in body_paths)]
            row = {
                'path': str(obj.GetPath()), 'room': room.GetName(), 'name': obj.GetName(), 'class': cls,
                'class_source': cls_source, 'aabb_min': lo, 'aabb_max': hi, 'meshes': meshes, 'triangles': triangles,
                'colliders': colliders, 'rigid_bodies': bodies, 'nested_rigid_bodies': nested, 'joints': joints,
                'mesh_merge_apis': merge,
            }
            row['group'] = group_of(row, cls_cfg)
            rows.append(row)
    return rows


def group_of(row, cls_cfg):
    cls, name = row['class'].lower(), row['name'].lower()
    if cls in cls_cfg['structure_classes']:
        return cls
    if cls in cls_cfg['opening_classes'] or any(name.startswith(c) for c in cls_cfg['opening_classes']):
        return 'opening'
    if row['aabb_min'] is None:
        return 'other'
    standing = (row['aabb_min'][2] <= cls_cfg['floor_standing_max_bottom_z_m']
                and row['aabb_max'][2] >= cls_cfg['floor_standing_min_top_z_m'])
    if not standing:
        return 'other'
    if any(soft in cls for soft in cls_cfg['soft_classes_exempt']):
        return 'soft_exempt'
    return 'floor_standing_obstacle'


def scene_prims_report(stage):
    """PhysicsScene prims, ground-plane candidates and lights anywhere in a stage."""
    from pxr import UsdPhysics

    scenes, planes, lights, total = [], [], [], 0
    for prim in stage.Traverse():
        total += 1
        type_name = prim.GetTypeName()
        if prim.IsA(UsdPhysics.Scene):
            scenes.append(str(prim.GetPath()))
        if type_name == 'Plane' or 'groundplane' in prim.GetName().lower():
            planes.append(str(prim.GetPath()))
        if type_name.endswith('Light'):
            lights.append({'path': str(prim.GetPath()), 'type': type_name})
    return {'prims': total, 'physics_scenes': scenes, 'ground_planes': planes, 'lights': lights}


def extents(rows):
    """Floor XY bounding box and whole-scene Z extent from the object rows."""
    floors = [r for r in rows if r['group'] == 'floor' and r['aabb_min']]
    boxed = [r for r in rows if r['aabb_min']]
    if not floors or not boxed:
        return None
    return {
        'floor_xy_min': [min(r['aabb_min'][i] for r in floors) for i in (0, 1)],
        'floor_xy_max': [max(r['aabb_max'][i] for r in floors) for i in (0, 1)],
        'scene_z': [min(r['aabb_min'][2] for r in boxed), max(r['aabb_max'][2] for r in boxed)],
    }


def episode_points_inside(ext, episodes):
    points = []
    for ep in episodes:
        points.append(('start', ep['episode_id'], ep['start_position']))
        points.append(('goal', ep['episode_id'], ep['goals']['position']))
    lo, hi = ext['floor_xy_min'], ext['floor_xy_max']
    outside = [(kind, eid, p) for kind, eid, p in points
               if not (lo[0] <= p[0] <= hi[0] and lo[1] <= p[1] <= hi[1])]
    return {'points': len(points), 'outside': outside, 'inside_fraction': 1.0 - len(outside) / len(points)}


def object_for_path(path, rows):
    """The object row whose prim path is a prefix of `path` (longest match), or None."""
    best = None
    for row in rows:
        p = row['path']
        if (path == p or path.startswith(p + '/')) and (best is None or len(p) > len(best['path'])):
            best = row
    return best


# ----------------------------------------------------------------------------------------------------------------
# Scene-query decisions (no Kit: the query functions are passed in)
# ----------------------------------------------------------------------------------------------------------------

def is_under(path, owner):
    return path == owner or path.startswith(owner + '/')


def own_hit_query(query, center, half, owner, trigger_hits, max_depth, pad=0.01, _depth=0):
    """Does the box (center, half extents) overlap a collider under `owner`?

    `query(center, half, owner) -> (hits_reported, own_collision_path_or_None)` must stop at the first own hit and
    have no cap of its own. If no own hit and the query reported >= trigger_hits hits (a possible internal cap),
    the box is split into 8 padded octants, recursively down to max_depth.
    """
    hits, own = query(center, half, owner)
    record = {'effective': own is not None, 'own_collision': own, 'queries': 1, 'max_hits': hits,
              'inconclusive': False}
    if own is not None:
        return record
    if hits < trigger_hits:
        return record
    if _depth >= max_depth:
        record['inconclusive'] = True
        return record
    sub_half = [h / 2.0 + pad for h in half]
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                sub_center = [c + s * h / 2.0 for c, s, h in zip(center, (sx, sy, sz), half)]
                sub = own_hit_query(query, sub_center, sub_half, owner, trigger_hits, max_depth, pad, _depth + 1)
                record['queries'] += sub['queries']
                record['max_hits'] = max(record['max_hits'], sub['max_hits'])
                record['inconclusive'] = record['inconclusive'] or sub['inconclusive']
                if sub['effective']:
                    record.update(effective=True, own_collision=sub['own_collision'], inconclusive=False)
                    return record
    return record


def floor_ray_summary(hits, rows, origin_z, floor_class, tolerance):
    """Downward ray hits [{'collision', 'distance'}] -> closest hit and the first floor-class hit within tolerance."""
    annotated = []
    for h in sorted(hits, key=lambda h: h['distance']):
        row = object_for_path(h['collision'], rows)
        annotated.append({'collision': h['collision'], 'distance': h['distance'], 'z': origin_z - h['distance'],
                          'object': row['path'] if row else None, 'class': row['class'] if row else None})
    floor_hits = [h for h in annotated if (h['class'] or '').lower() == floor_class.lower()]
    within = [h for h in floor_hits if abs(h['z']) <= tolerance]
    return {'hits': annotated[:20], 'hit_count': len(annotated), 'closest': annotated[0] if annotated else None,
            'floor_hit': within[0] if within else None, 'nearest_floor_class_hit': floor_hits[0] if floor_hits else None}


def body_motion(before, after, groups):
    """Per body: displacement and rotation between two pose maps {path: (xyz, quat_xyzw)}."""
    rows = []
    for path, meta in groups.items():
        row = dict(meta, path=path, found=path in before and path in after)
        if row['found']:
            (p0, q0), (p1, q1) = before[path], after[path]
            row['displacement_m'] = math.dist(p0, p1)
            row['rotation_deg'] = quat_angle_deg(q0, q1)
        rows.append(row)
    return rows


def probe_drop(before, after, probe_path, cfg):
    if probe_path not in before or probe_path not in after:
        return {'ok': False, 'reason': 'probe not readable'}
    drop = before[probe_path][0][2] - after[probe_path][0][2]
    lateral = math.dist(before[probe_path][0][:2], after[probe_path][0][:2])
    ok = abs(drop - cfg['expected_drop_m']) <= cfg['tolerance_m'] and lateral <= cfg['tolerance_m']
    return {'ok': ok, 'drop_m': drop, 'lateral_m': lateral, 'expected_drop_m': cfg['expected_drop_m']}


def readback_check(readback, targets, max_error_m):
    """Camera world positions read back vs targets, both {camera: (x, y, z)}."""
    errors = {name: math.dist(readback[name], targets[name]) for name in targets if name in readback}
    missing = sorted(set(targets) - set(readback))
    worst = max(errors.values()) if errors else None
    return {'ok': not missing and worst is not None and worst <= max_error_m, 'errors_m': errors,
            'max_error_m': worst, 'missing': missing}


# ----------------------------------------------------------------------------------------------------------------
# Geometry helpers
# ----------------------------------------------------------------------------------------------------------------

def yaw_quat_wxyz(yaw_deg):
    h = math.radians(yaw_deg) / 2.0
    return (math.cos(h), 0.0, 0.0, math.sin(h))


def quat_mul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw)


def quat_rotate(q, v):
    w, x, y, z = q
    vx, vy, vz = v
    # v' = v + 2w(u x v) + 2 u x (u x v), u = (x, y, z)
    cx, cy, cz = y * vz - z * vy, z * vx - x * vz, x * vy - y * vx
    ccx, ccy, ccz = y * cz - z * cy, z * cx - x * cz, x * cy - y * cx
    return (vx + 2 * (w * cx + ccx), vy + 2 * (w * cy + ccy), vz + 2 * (w * cz + ccz))


def compose(parent_pos, parent_q, local_pos, local_q):
    rotated = quat_rotate(parent_q, local_pos)
    return (tuple(p + r for p, r in zip(parent_pos, rotated)), quat_mul(parent_q, local_q))


def quat_angle_deg(qa, qb):
    """Rotation angle between two quaternions (same component order), float64 after normalising both."""
    na = math.sqrt(sum(float(a) * float(a) for a in qa))
    nb = math.sqrt(sum(float(b) * float(b) for b in qb))
    if na == 0.0 or nb == 0.0:
        return float('nan')
    dot = abs(sum((float(a) / na) * (float(b) / nb) for a, b in zip(qa, qb)))
    return math.degrees(2.0 * math.acos(min(1.0, dot)))


# ----------------------------------------------------------------------------------------------------------------
# Image metrics (numpy)
# ----------------------------------------------------------------------------------------------------------------

def rgb_metrics(rgb, dark_max_channel):
    import numpy as np

    img = np.asarray(rgb)[..., :3].astype(np.float32)
    grey = 0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2]
    return {'mean_grey': float(grey.mean()), 'std_grey': float(grey.std()),
            'dark_fraction': float((img.max(axis=-1) < dark_max_channel).mean())}


def depth_metrics(depth):
    import numpy as np

    d = np.asarray(depth, dtype=np.float32)
    valid = np.isfinite(d) & (d > 0)
    return {'valid_fraction': float(valid.mean()),
            'median_m': float(np.median(d[valid])) if valid.any() else None}


def rgb_valid(m, render_cfg):
    lo, hi = render_cfg['rgb_mean_grey']
    return lo <= m['mean_grey'] <= hi and m['std_grey'] >= render_cfg['rgb_min_std_grey'] and \
        m['dark_fraction'] <= render_cfg['rgb_max_dark_fraction']


def depth_valid(m, render_cfg):
    lo, hi = render_cfg['depth_median_m']
    return m['valid_fraction'] >= render_cfg['depth_min_valid_fraction'] and m['median_m'] is not None and \
        lo <= m['median_m'] <= hi


# ----------------------------------------------------------------------------------------------------------------
# The gate
# ----------------------------------------------------------------------------------------------------------------

def memory_verdict(isaac_peak_mib, gpu_cfg):
    if isaac_peak_mib is None:
        return 'MISSING', None
    projected = (gpu_cfg['vla_client_peak_mib'] + isaac_peak_mib + gpu_cfg['robot_lidar_allowance_mib']
                 + gpu_cfg['device_overhead_mib'])
    if isaac_peak_mib <= gpu_cfg['isaac_peak_pass_max_mib']:
        return 'PASS', projected
    if isaac_peak_mib <= gpu_cfg['isaac_peak_marginal_max_mib']:
        return 'MARGINAL', projected
    return 'FAIL', projected


def _check(name, ok, detail):
    return {'check': name, 'verdict': 'PASS' if ok else 'FAIL', 'detail': detail}


def evaluate(result, thresholds, isaac_peak_mib=None):
    """Per-check verdicts for a D.1b run record. Missing sections FAIL; nothing is inferred."""
    checks = []
    st, thr = result.get('static') or {}, thresholds['stage']
    dep = st.get('dependencies') or {}
    checks.append(_check('S1_local_paths_resolve',
                         bool(dep) and len(dep.get('local_unresolved', [1])) <= thr['max_unresolved_local_paths']
                         and len(dep.get('non_local', [1])) <= thr['max_non_local_asset_paths'],
                         {'local_unresolved': dep.get('local_unresolved'), 'non_local': dep.get('non_local'),
                          'bare_mdl_reported': dep.get('bare_mdl_unresolved'),
                          'unreal_metadata_reported': dep.get('unreal_metadata_unresolved_count'),
                          'errors': (result.get('static_errors') or {}).get('dependencies')}))
    units = st.get('layer_units') or []
    bad_units = [u for u in units if u['meters_per_unit'] != thr['meters_per_unit'] or u['up_axis'] != thr['up_axis']]
    checks.append(_check('S2_metres_and_z_up', bool(units) and not bad_units,
                         {'layers': len(units), 'mismatched': bad_units[:20], 'mismatched_count': len(bad_units)}))
    kit = result.get('kit_stage') or {}
    scene_scenes = (st.get('prims') or {}).get('physics_scenes')
    kit_scenes = kit.get('physics_scenes')
    kit_planes = kit.get('ground_planes')
    checks.append(_check('S3_one_physics_scene',
                         scene_scenes is not None and kit_scenes is not None
                         and len(scene_scenes) == thr['physics_scenes_in_scene_file']
                         and len(kit_scenes) == thr['physics_scenes_in_kit_stage'],
                         {'scene_file': scene_scenes, 'kit_stage': kit_scenes,
                          'scene_prim_xform_ops': kit.get('scene_prim_xform_ops')}))
    checks.append(_check('S4_no_extra_ground_plane',
                         kit_planes is not None and len(kit_planes) <= thr['max_extra_ground_planes'],
                         {'ground_planes': kit_planes}))
    ext, inside = st.get('extents'), st.get('episode_points')
    ext_ok = False
    if ext and inside:
        span_x = ext['floor_xy_max'][0] - ext['floor_xy_min'][0]
        span_y = ext['floor_xy_max'][1] - ext['floor_xy_min'][1]
        span_z = ext['scene_z'][1] - ext['scene_z'][0]
        lo, hi = thr['floor_xy_extent_m']
        zlo, zhi = thr['scene_z_extent_m']
        ext_ok = (lo <= span_x <= hi and lo <= span_y <= hi and zlo <= span_z <= zhi
                  and inside['inside_fraction'] >= thr['episode_points_inside_floor_xy_bbox_fraction'])
    checks.append(_check('S5_metre_scale_and_episode_frame', ext_ok, {'extents': ext, 'episode_points': inside}))

    col, ccfg = result.get('collision') or {}, thresholds['collision']
    per_group = {}
    for row in col.get('objects', []):
        g = per_group.setdefault(row['group'], {'objects': 0, 'effective': 0, 'not_effective': [], 'inconclusive': []})
        g['objects'] += 1
        if row['effective']:
            g['effective'] += 1
        else:
            g['not_effective'].append({'path': row['path'], 'class': row['class']})
            if row.get('inconclusive'):
                g['inconclusive'].append(row['path'])
    ok = bool(col.get('objects'))
    for group, need in ccfg['effective_fraction_required'].items():
        g = per_group.get(group)
        if not g or g['effective'] / g['objects'] < need:   # an empty gated group means the classification failed
            ok = False
    checks.append(_check('C2_colliders_effective_in_physx', ok,
                         {'groups': per_group, 'error': (result.get('section_errors') or {}).get('collision')}))
    rays = col.get('floor_rays') or {}
    ray_ok = set(rays) == {'A', 'B'}
    for r in rays.values():
        hit = r.get('floor_hit')
        if not (hit and (hit.get('class') or '').lower() == ccfg['floor_ray_must_hit_class'].lower()
                and abs(hit['z']) <= ccfg['floor_hit_z_tolerance_m']):
            ray_ok = False
    checks.append(_check('C3_floor_under_both_poses', ray_ok,
                         {k: {'floor_hit': v.get('floor_hit'), 'closest': v.get('closest'),
                              'closest_front_face': v.get('closest_front_face')} for k, v in rays.items()}))

    phys, pcfg = result.get('physics') or {}, thresholds['physics']
    bodies = phys.get('bodies', [])
    gated = [b for b in bodies if b['group'] in pcfg['gated_groups']]
    gated_found = [b for b in gated if b.get('found')]
    moved = [b for b in gated_found if not (b['displacement_m'] <= pcfg['max_displacement_m']
                                            and b['rotation_deg'] <= pcfg['max_rotation_deg'])]
    probe = phys.get('readout_probe') or {}
    readout_valid = bool(probe.get('ok')) and phys.get('readout') in ('rigid_body_view', 'get_rigidbody_transformation')
    # A body PhysX never created cannot move; it is listed, and C2 decides whether its collider works.
    phys_ok = readout_valid and bool(gated_found) and \
        phys.get('simulated_s', 0) + 1e-9 >= pcfg['settle_seconds'] and not moved
    checks.append(_check('P1_static_scene_stays_put', phys_ok,
                         {'readout': phys.get('readout'), 'readout_probe': probe,
                          'probes_by_readout': phys.get('probes_by_readout'),
                          'simulated_s': phys.get('simulated_s'), 'bodies': len(bodies), 'gated_bodies': len(gated),
                          'gated_found_in_physx': len(gated_found),
                          'gated_not_found': [b['path'] for b in gated if not b.get('found')][:20],
                          'gated_failures': moved[:20], 'gated_failure_count': len(moved),
                          'reported_moving': [b for b in bodies if b['group'] not in pcfg['gated_groups']
                                              and b.get('found') and not (
                                                  b['displacement_m'] <= pcfg['max_displacement_m']
                                                  and b['rotation_deg'] <= pcfg['max_rotation_deg'])][:20],
                          'error': (result.get('section_errors') or {}).get('physics')}))

    rcfg = thresholds['render']
    renders = result.get('render') or {}
    for pose in ('A', 'B'):
        r = renders.get(pose) or {}
        readback = (renders.get('poses_check') or {}).get(pose) or {}
        ok = bool(r) and bool(readback.get('ok')) and \
            r.get('consecutive_valid_max', 0) >= rcfg['consecutive_valid_required'] and \
            r.get('first_valid_s') is not None and r['first_valid_s'] <= rcfg['first_valid_frame_timeout_s']
        checks.append(_check('R_frames_valid_pose_' + pose, ok,
                             {'camera_readback': readback,
                              **{k: r.get(k) for k in ('iterations', 'first_valid_iteration', 'first_valid_s',
                                                       'consecutive_valid_max', 'last_metrics', 'error')}}))

    mem, projected = memory_verdict(isaac_peak_mib, thresholds['gpu_memory'])
    checks.append({'check': 'M1_isaac_gpu_peak', 'verdict': mem,
                   'detail': {'isaac_peak_mib': isaac_peak_mib, 'projected_d1d_device_peak_mib': projected,
                              'device_total_mib': thresholds['gpu_memory']['device_total_mib']}})
    others_ok = all(c['verdict'] == 'PASS' for c in checks if c['check'] != 'M1_isaac_gpu_peak')
    admitted = others_ok and mem in ('PASS', 'MARGINAL')
    return {'checks': checks, 'admit_to_d1c': admitted,
            'failed': [c['check'] for c in checks if c['verdict'] not in ('PASS', 'MARGINAL')]}
