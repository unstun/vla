"""Source precision correspondence must preserve real obstacles and unknowns."""
import numpy as np
from source_material_association import SourceMaterialAssociation
floor=np.array([[[0,0,0],[1,0,0],[1,1,0]],[[0,0,0],[1,1,0],[0,1,0]]],float)
f=SourceMaterialAssociation(floor,floor)
one=np.nextafter(np.float32(1),np.float32(np.inf));far=one
for _ in range(7):far=np.nextafter(far,np.float32(np.inf))
records=np.array([[.5,.5,-.01,1,0,0],[one,.5,-.01,1,0,0],[far,.5,-.01,1,0,0],[.5,.5,.01,1,0,0],[.5,.5,.01,0,0,1],[.5,.5,.260001,0,0,1],[.5,.5,.3,0,0,1]],np.float32)
assert f.classify(records,0).tolist()==[True,True,False,False,True,False,False]
assert not f.classify(records,1).any()
# A source riser whose almost-vertical XY height projection is ill conditioned.
t=np.array([[[-6.328490257263184,5.7008137702941895,.162181094288826],[-4.198254585266113,5.7008137702941895,.162181094288826],[-4.198254585266113,5.700818061828613,.05803000181913376]]])
f=SourceMaterialAssociation(t,t)
r=np.array([[-4.882636547088623,5.700817584991455,.09252583235502243,0,1,0]],np.float32)
assert f.matches(r[0]) and f.classify(r,.05803030848503115)[0]
# Beyond the declared arithmetic envelope stays unmatched/solid.
far=r.copy();far[0,1]+=.001
assert not f.matches(far[0]) and not f.classify(far,.05803030848503115)[0]
assert not f.classify(r,1.)[0]
# A real high wall is never reclassified merely for being close to its mesh.
wall=np.array([[[-6,5.7,0],[-4,5.7,0],[-4,5.7,2]],[[-6,5.7,0],[-4,5.7,2],[-6,5.7,2]]],float)
w=SourceMaterialAssociation(wall,wall);p=np.array([[-5,5.7,.1,0,1,0]],np.float32)
assert w.matches(p[0]) and not w.classify(p,0)[0]
# A source surface exceeding the critical height band is not wholly terrain.
high=t.copy();high[:,:,2]+=.3
h=SourceMaterialAssociation(high,high);q=r.copy();q[:,2]+=.3
assert not h.classify(q,.05803030848503115)[0]
# Normal-incompatible and zero-normal points provide no registration evidence.
wrong=r.copy();wrong[:,3:]=[0,0,1]
assert not f.matches(wrong[0])
unknown=r.copy();unknown[:,3:]=0
assert not f.matches(unknown[0])
print('controls=15 failures=0')
