"""Finite double-sided faces plus interiors of certified closed solids only."""
from pathlib import Path
import importlib.util,sys
import numpy as np
from source_topology import prepare

parent=Path(__file__).resolve().parent.parent/'v266/surface_model.py'
spec=importlib.util.spec_from_file_location('frozen_finite_surface_v266',parent)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class SurfaceModel(module.SurfaceModel):
    def __init__(self,triangles,**kwargs):
        normalized,self.solid_ids,self.topology=prepare(triangles)
        super().__init__(normalized,**kwargs)

    def occupied_axis_interval(self,x,y,ground,view):
        hits=self.vertical_hits(x,y)
        cap_heights=[z for z,n,i in hits if self.upward[i] and abs(z-ground)<self.step]
        terrain_top=max(cap_heights,default=-float('inf'))
        events={}
        for z,n,i in hits:
            gid=int(self.solid_ids[i])
            if gid>=0:events.setdefault(gid,[]).append((z,1 if n>0 else -1))
        for levels in events.values():
            # Deduplicate coincident adjacent faces without quantizing heights.
            grouped=[]
            for z,sign in sorted(levels,reverse=True):
                if grouped and abs(z-grouped[-1][0])<=module.EPS:grouped[-1][1].add(sign)
                else:grouped.append([z,{sign}])
            winding=0;previous=float('inf')
            for z,signs in grouped:
                if winding>0 and min(previous,view['zhi'])>max(z,view['zlo'],terrain_top)+module.EPS:return True
                winding+=sum(signs);previous=z
            if winding>0 and min(previous,view['zhi'])>max(view['zlo'],terrain_top)+module.EPS:return True
        return False
