"""Reuse source topology operations; change winding only, never geometry."""
import hashlib,inspect
import numpy as np
import trimesh

def prepare(triangles):
    tri=np.asarray(triangles,float)
    vertices,inverse=np.unique(tri.reshape(-1,3),axis=0,return_inverse=True)
    faces=inverse.reshape(-1,3)
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False,validate=False)
    groups=trimesh.graph.connected_components(mesh.face_adjacency,nodes=np.arange(len(faces)),engine='scipy')
    normalized=tri.copy();solid_ids=np.full(len(tri),-1,dtype=np.int32);records=[]
    for group in sorted(groups,key=lambda g:int(min(g))):
        group=np.sort(group)
        sub=trimesh.Trimesh(vertices=vertices.copy(),faces=faces[group].copy(),process=False,validate=False)
        watertight=bool(sub.is_watertight)
        if watertight:trimesh.repair.fix_normals(sub,multibody=False)
        volume=watertight and bool(sub.is_volume)
        assert np.array_equal(sub.vertices,vertices),'Geometry coordinates changed'
        assert np.array_equal(np.sort(sub.faces,axis=1),np.sort(faces[group],axis=1)),'Source face connectivity changed'
        if volume:
            gid=len(records);solid_ids[group]=gid;normalized[group]=vertices[sub.faces]
        else:gid=-1
        records.append(dict(first_face=int(group[0]),faces=len(group),watertight=watertight,
            certified_closed_volume=volume,solid_id=gid,
            bounds=[tri[group].min(axis=(0,1)).tolist(),tri[group].max(axis=(0,1)).tolist()]))
    receipt=dict(library='trimesh',version=trimesh.__version__,objects=len(records),
        certified_closed_volumes=sum(r['certified_closed_volume'] for r in records),
        closed_volume_faces=int((solid_ids>=0).sum()),surface_only_faces=int((solid_ids<0).sum()),
        winding_changed_faces=int(np.any(normalized!=tri,axis=(1,2)).sum()),vertices_unchanged=True,
        distance_welding=False,hole_filling=False,source_face_connectivity_unchanged=True,
        library_source_sha256={name:hashlib.sha256(inspect.getsource(module).encode()).hexdigest() for name,module in [('graph',trimesh.graph),('repair',trimesh.repair)]},objects_detail=records)
    return normalized,solid_ids,receipt
