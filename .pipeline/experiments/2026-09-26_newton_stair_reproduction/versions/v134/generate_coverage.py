"""Build a pinned, negative-only static-map supplement on gpu5070ti."""
from pathlib import Path
import hashlib,json,subprocess,sys
import numpy as np
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
TASK=Path('/data/sun/vla_mppi_20261009')
sys.path.insert(0,str(BASE/'scripts'))
from scene_assets import building_mesh
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    out=TASK/'support_coverage_v134';out.mkdir(exist_ok=False)
    mesh=BASE/'inputs/building.usda'
    assert sha(mesh)=='e55e4a9507441b8f1788503f909505a49b63d6eb36f6882ba782aee7c38a5d39'
    floor=TASK/'fixed_curve_input/physical_floor.f32'
    original=json.loads((HERE/'physical_floor_input.json').read_text())
    assert sha(floor)==original['files']['physical_floor.f32']['sha256']
    vertices,faces,_=building_mesh();triangles=vertices[faces].astype('<f8')
    triangles.tofile(out/'triangles.f64')
    subprocess.run(['g++','-std=c++17','-O2',str(HERE/'support_coverage.cpp'),'-o',str(out/'generate')],check=True)
    result=subprocess.check_output([str(out/'generate'),str(out/'triangles.f64'),str(floor),str(out/'partial.txt')],text=True)
    points=np.loadtxt(out/'partial.txt');assert points.ndim==2 and points.shape[1]==3 and np.isfinite(points).all()
    fnv=14695981039346656037
    for v in (out/'partial.txt').read_bytes():fnv=((fnv^v)*1099511628211)&((1<<64)-1)
    receipt={'schema':'static_support_coverage_v1','source_mesh_sha256':sha(mesh),
        'source_floor_sha256':sha(floor),'generator_cpp_sha256':sha(HERE/'support_coverage.cpp'),
        'generator_py_sha256':sha(Path(__file__)),'sampling_m':.025,'cell_resolution_m':.1,
        'height_bound_m':.26,'dilation_radius_m':.35,'counts':json.loads(result),
        'file':'/task/support_coverage_v134/partial.txt','sha256':sha(out/'partial.txt'),'fnv64':str(fnv),
        'bytes':(out/'partial.txt').stat().st_size,'negative_only':True,
        'claim':'Offline original static Building map supplement. No online mesh or physical-state input.'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':main()
