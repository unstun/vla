"""Reuse frozen v272 raw-point distances with explicit material dependency injection."""
from pathlib import Path
import hashlib,sys,os
os.environ["OPENBLAS_NUM_THREADS"]="1";os.environ["OMP_NUM_THREADS"]="1"
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'v272'))
import raw_source_oracle as frozen
from source_material_association import SourceMaterialAssociation
BASE=Path('/data/sun/vla_mppi_20261009')
tri=BASE/'source_topology_v268/triangles_oriented.f64';meta=BASE/'source_topology_v268/closed_volumes.txt'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(tri)=='8d329c5453bc7859434e9018c50a9f55bb4c9def2aa75da301b97dd6556dfb20'
assert sha(meta)=='ed00e6322db41354d4823389d952b1649f9fde738175b4577985ba4c139315e4'
labels=np.array(list(map(int,meta.read_text().split('\nF\n')[1].splitlines())))
association=SourceMaterialAssociation(frozen.tri,np.fromfile(tri,dtype='<f8').reshape(-1,3,3),labels)
original_material=frozen.floor_material

def activate():
    frozen.floor_material=lambda records,_tri,_tree,ground:association.classify(records,ground)

def deactivate():frozen.floor_material=original_material
margin=frozen.margin
