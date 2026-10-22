"""Locate cost barriers under measured native support and soft-body witnesses.

This explores candidate passages only. Endpoint samples and an atlas cannot
authorize a segment; exact whole-connector tests are a separate required gate.
"""
from pathlib import Path
import csv,heapq,json,numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components,breadth_first_order
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'endpoint_connectivity_v244/diagnostic'
def main():
    nl,nx,ny,res,cx,cy=map(float,(OUT/'graph_meta.txt').read_text().split());nl,nx,ny=int(nl),int(nx),int(ny)
    a=np.fromfile(OUT/'graph_states.f64',dtype='<f8').reshape(nl,nx,ny,6)
    checks=np.full((nl,nx,ny,4),255);solid=np.full(checks.shape,-1.)
    for r in csv.DictReader((OUT/'support_grid/screen.csv').open()):
        idx=tuple(map(int,r['id'].split('_')));checks[idx]=int(r['static_verdict']);solid[idx]=float(r['atlas_solid_margin'])
    report={};queries=json.loads((OUT/'graph_summary.json').read_text())['queries']
    for mode in ('cost_only','support_only','support_and_atlas'):
        rr=[];cc=[];k=0
        oknode=(a[k,:,:,5]>0)&(np.abs(a[k,:,:,1]-.05804443359375)<.2)
        good=np.broadcast_to(oknode[...,None],(nx,ny,4)).copy()
        if mode!='cost_only':good &= checks[k]==0
        if mode=='support_and_atlas':good &= solid[k]>=0
        xx,yy=np.indices((nx,ny))
        for dx,dy in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
            h=int(np.rint(np.arctan2(dy,dx)/(np.pi/4)))%4
            tx,ty=xx+dx,yy+dy;inside=(tx>=0)&(tx<nx)&(ty>=0)&(ty<ny)
            tx,ty=np.clip(tx,0,nx-1),np.clip(ty,0,ny-1)
            ok=inside&good[:,:,h]&good[tx,ty,h]
            rr.extend((xx[ok]*ny+yy[ok]).tolist());cc.extend((tx[ok]*ny+ty[ok]).tolist())
        g=coo_matrix((np.ones(len(rr)),(rr,cc)),shape=(nx*ny,nx*ny)).tocsr()
        n,labels=connected_components(g,directed=True,connection='strong')
        start=queries['A04']['start']['index'][1:];goal=queries['A02']['start']['index'][1:]
        order,prev=breadth_first_order(g,start[0]*ny+start[1],directed=True)
        target=goal[0]*ny+goal[1];p=target;path=[]
        if p in order:
            while p>=0:path.append(divmod(p,ny));p=int(prev[p])
            path.reverse()
        blocked=[dict(index=list(p),world=[(p[0]-nx//2)*res+cx,(p[1]-ny//2)*res+cy],cost=float(a[0,*p,0])) for p in path if a[0,*p,0]>20]
        report[mode]=dict(reachable=len(order),A04_to_A02=bool(path),path_cells=len(path),blocked_cells=blocked)
        if path:np.savetxt(OUT/f'passage_{mode}.csv',np.array([[(x-nx//2)*res+cx,(y-ny//2)*res+cy,a[0,x,y,1]+.3,a[0,x,y,0]] for x,y in path]),delimiter=',',header='x,y,z,cost')
        report[mode]['endpoint_components']={case:{side:int(labels[e[side]['index'][1]*ny+e[side]['index'][2]]) for side in ('start','goal') if e[side]['index'][0]==0} for case,e in queries.items()}
    (OUT/'passage_summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
