"""Display-only restoration of the previous Building review's dark Lite3."""
import hashlib
import json

DARK_COLOR = (0.065, 0.08, 0.09)
DARK_ROUGHNESS = 0.55


def geometry_physics_fingerprint(root):
    """Exclude only visual material/display attributes; retain geometry and physics."""
    from pxr import Usd
    rows = []
    for prim in Usd.PrimRange(root, Usd.TraverseInstanceProxies()):
        attributes = []
        for attr in prim.GetAttributes():
            name = attr.GetName()
            if name.startswith(('material:', 'primvars:display', 'inputs:', 'outputs:')):
                continue
            attributes.append((name, str(attr.Get())))
        relationships = [(rel.GetName(), [str(p) for p in rel.GetTargets()])
                         for rel in prim.GetRelationships()
                         if not rel.GetName().startswith('material:')]
        rows.append((str(prim.GetPath()), prim.GetTypeName(), sorted(attributes), sorted(relationships)))
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def apply_robot_visual(stage, style):
    from pxr import Usd, UsdGeom, UsdShade
    root = stage.GetPrimAtPath('/World/envs/env_0/Robot')
    if not root.IsValid():
        raise RuntimeError('robot visual root missing')
    before = geometry_physics_fingerprint(root)
    meshes = [p for p in Usd.PrimRange(root, Usd.TraverseInstanceProxies()) if p.IsA(UsdGeom.Mesh)]
    record = {'style': style, 'robot_root': str(root.GetPath()), 'mesh_count': len(meshes),
              'geometry_physics_before_sha256': before}
    if style == 'black_review':
        import isaaclab.sim as sim_utils
        config = sim_utils.PreviewSurfaceCfg(diffuse_color=DARK_COLOR, roughness=DARK_ROUGHNESS)
        config.func('/World/ReviewRobotMaterial', config)
        material = UsdShade.Material(stage.GetPrimAtPath('/World/ReviewRobotMaterial'))
        UsdShade.MaterialBindingAPI.Apply(root).Bind(material, UsdShade.Tokens.strongerThanDescendants)
        bindings = [str(UsdShade.MaterialBindingAPI(p).ComputeBoundMaterial()[0].GetPath()) for p in meshes]
        if not meshes or any(path != '/World/ReviewRobotMaterial' for path in bindings):
            raise RuntimeError('dark material was not bound to every robot mesh')
        record.update(diffuse_color=list(DARK_COLOR), roughness=DARK_ROUGHNESS,
                      bound_mesh_count=len(bindings), material_path='/World/ReviewRobotMaterial',
                      provenance='.pipeline/experiments/2026-09-08_new_building_lite3_dynamics/render_style_r6.py:72-75')
    elif style != 'native':
        raise ValueError('unknown robot visual style')
    after = geometry_physics_fingerprint(root)
    record.update(geometry_physics_after_sha256=after, geometry_physics_unchanged=before == after)
    if before != after:
        raise RuntimeError('display override altered geometry or physics attributes')
    return record
