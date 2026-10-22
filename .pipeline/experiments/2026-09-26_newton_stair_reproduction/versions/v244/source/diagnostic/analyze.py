"""Directed native-slice graph analysis; no planner substitutes in scored calls."""
from pathlib import Path
import collections,hashlib,heapq,json,pickle,re
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components,breadth_first_order
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'endpoint_connectivity_v244/diagnostic'
def main():
    l,nx,ny,res,cx,cy=map(float,(OUT/'graph_meta.txt').read_text().split())
    l,nx,ny=int(l),int(nx),int(ny);shape=(l,nx,ny)
    a=np.fromfile(OUT/'graph_states.f64',dtype='<f8').reshape(*shape,6)
    cost,height,ele,decide,zbin,valid=[a[...,i] for i in range(6)]
    ids=np.arange(l*nx*ny).reshape(shape);layer,x,y=np.indices(shape)
    rows=[];cols=[]
    for dx,dy in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
        tx,ty=x+dx,y+dy;inside=(tx>=0)&(tx<nx)&(ty>=0)&(ty<ny)
        tx,ty=np.clip(tx,0,nx-1),np.clip(ty,0,ny-1);tl=decide.astype(int)
        ok=inside&((cost[tl,tx,ty]<=20)|((np.abs(ele[tl,tx,ty])>=.5)&(np.abs(height[tl,tx,ty]-height)<=.3)))
        rows.append(ids[ok]);cols.append(ids[tl,tx,ty][ok])
    row,col=np.concatenate(rows),np.concatenate(cols)
    graph=coo_matrix((np.ones(len(row),dtype=np.uint8),(row,col)),shape=(ids.size,ids.size)).tocsr()
    count,scc=connected_components(graph,directed=True,connection='strong')
    wcount,wcc=connected_components(graph,directed=True,connection='weak')
    active=(valid>0)&((cost<=20)|(np.abs(ele)>=.5))
    def distributions(labels,mask):
        unique,n=np.unique(labels[mask.ravel()],return_counts=True)
        return sorted((dict(id=int(k),stored_states=int(v)) for k,v in zip(unique,n)),key=lambda p:-p['stored_states'])
    report=dict(shape=list(shape),states=int(ids.size),accepted_edges=int(len(row)),
        native_search_log_sha256=hashlib.sha256((OUT/'search.log').read_bytes()).hexdigest(),
        graph_definition='Stored slice nodes; exact installed DecideLayer and eight-neighbor cost/gateway admission. A* additionally merges equal(height_bin,x,y) closed keys.',
        strong_components_with_active_states=distributions(scc,active),
        weak_components_with_active_states=distributions(wcc,active),floors={},queries={})
    source=pickle.loads((BASE/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/inputs/new_building.pickle').read_bytes())
    original=source['data'][0].astype(float)
    assert original.shape==shape
    def floor_components(k,base):
        mask=(valid[k]>0)&(base[k]<=20)&(np.abs(height[k]-(.05804443359375 if k==0 else 4.53125))<=.2)
        rr=[];cc=[]
        ix,iy=np.nonzero(mask)
        for dx,dy in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
            xx,yy=ix+dx,iy+dy;inside=(xx>=0)&(xx<nx)&(yy>=0)&(yy<ny)
            xx,yy=xx[inside],yy[inside];sx,sy=ix[inside],iy[inside];ok=mask[xx,yy]
            rr.extend((sx[ok]*ny+sy[ok]).tolist());cc.extend((xx[ok]*ny+yy[ok]).tolist())
        g=coo_matrix((np.ones(len(rr)),(rr,cc)),shape=(nx*ny,nx*ny)).tocsr()
        _,labels=connected_components(g,directed=False)
        return mask,labels.reshape(nx,ny),distributions(labels,mask)
    floor_labels={}
    for k in (0,7):
        m,lab,d=floor_components(k,cost);bm,blab,bd=floor_components(k,original)
        floor_labels[k]=lab
        report['floors'][str(k)]=dict(native_components=d,original_pre_v135_components=bd,
            newly_threshold_blocked=int(np.count_nonzero(bm&~m)))
    for case in sorted((BASE/'generalization_v242/cases').iterdir()):
        if not (case/'endpoints.txt').exists():continue
        ep=np.loadtxt(case/'endpoints.txt')[:6].reshape(2,3)
        entry={}
        indices=[]
        for name,p in zip(('start','goal'),ep):
            ix,iy=(np.rint((p[:2].astype(np.float32)-[cx,cy])/res).astype(int)+[nx//2,ny//2])
            candidates=np.where(valid[:,ix,iy]>0)[0]
            k=int(candidates[np.argmin(np.abs(height[candidates,ix,iy].astype(np.float32)-np.float32(p[2])))])
            idx=int(ids[k,ix,iy]);indices.append(idx)
            entry[name]=dict(index=[k,int(ix),int(iy)],world=p.tolist(),cost=float(cost[k,ix,iy]),
                original_cost=float(original[k,ix,iy]),decided_layer=int(decide[k,ix,iy]),
                scc=int(scc[idx]),wcc=int(wcc[idx]),floor_component=int(floor_labels[k][ix,iy]) if k in floor_labels else None)
        for reverse in (False,True):
            key='reverse' if reverse else 'forward';path=OUT/f"visited_{case.name}{'_reverse' if reverse else ''}.csv"
            if not path.stat().st_size:entry[key]=dict(visited=0);continue
            v=np.loadtxt(path,delimiter=',',dtype=int).reshape(-1,3)
            layers,n=np.unique(v[:,0],return_counts=True)
            order=breadth_first_order(graph,indices[int(reverse)],directed=True,return_predecessors=False)
            entry[key]=dict(visited=len(v),layers=dict(zip(map(str,layers.tolist()),n.tolist())),
                visited_xy_bounds=[((v[:,1:].min(0)-[nx//2,ny//2])*res+[cx,cy]).tolist(),((v[:,1:].max(0)-[nx//2,ny//2])*res+[cx,cy]).tolist()],
                exhaustive_stored_reachable=len(order),target_stored_reachable=bool(indices[1-int(reverse)] in order))
        report['queries'][case.name]=entry
    # Minimum-number-of-v135-blocked-cell bridge on the original downstairs
    # graph, independent of any wall/column interpretation.
    start=report['queries']['A04']['start']['index'][1:];goal=report['queries']['A02']['start']['index'][1:]
    validfloor=(valid[0]>0)&(original[0]<=20)&(np.abs(height[0]-.05804443359375)<=.2)
    q=[(0.,tuple(start))];dist={tuple(start):0.};prev={}
    while q:
        d,p=heapq.heappop(q)
        if d!=dist[p]:continue
        if p==tuple(goal):break
        for dx,dy in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
            t=(p[0]+dx,p[1]+dy)
            if not(0<=t[0]<nx and 0<=t[1]<ny and validfloor[t]):continue
            nd=d+float(cost[0][t]>20)*1000+np.hypot(dx,dy)
            if nd<dist.get(t,float('inf')):dist[t]=nd;prev[t]=p;heapq.heappush(q,(nd,t))
    bridge=[];p=tuple(goal)
    if p in dist:
        while p!=tuple(start):bridge.append(p);p=prev[p]
        bridge.append(p);bridge.reverse()
    report['minimum_v135_bridge']=dict(found=bool(bridge),blocked_cells=[dict(index=list(p),
        world=[(p[0]-nx//2)*res+cx,(p[1]-ny//2)*res+cy],
        native_cost=float(cost[0][p]),original_cost=float(original[0][p])) for p in bridge if cost[0][p]>20])
    np.savetxt(OUT/'minimum_bridge.csv',np.array([[(x-nx//2)*res+cx,(y-ny//2)*res+cy,height[0,x,y]+.3,cost[0,x,y],original[0,x,y]] for x,y in bridge]),delimiter=',',header='x,y,body_z,cost,original_cost')
    (OUT/'graph_summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('shape','accepted_edges','floors','minimum_v135_bridge')},indent=2))
if __name__=='__main__':main()
